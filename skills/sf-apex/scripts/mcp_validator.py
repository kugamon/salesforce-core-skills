#!/usr/bin/env python3
"""
Apex MCP Deployment Validator
===============================

Validates Apex code being deployed via Salesforce MCP metadata tools.

Handles metadata_create, metadata_update, and tooling_api_dml for
ApexClass and ApexTrigger metadata types. Extracts the code body from
the MCP params, writes to a temp file, and delegates to the local
ApexValidator (150-point scoring).

For data operation validation (soql_query, sobject_dml), use
sf-data instead.

Input format:
{
  "tool": "metadata_create" | "metadata_update" | "tooling_api_dml",
  "params": { ... MCP tool parameters ... },
  "context": { "purpose": "optional description" }
}
"""

import os
import re
import sys
import tempfile
from typing import Any

# ═══════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════

SUPPORTED_TOOLS = ("metadata_create", "metadata_update", "tooling_api_dml")
APEX_METADATA_TYPES = ("ApexClass", "ApexTrigger")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════════════════════════════════════
# Code body extraction
# ═══════════════════════════════════════════════════════════════════════

def _extract_code_body(tool: str, params: dict[str, Any]) -> tuple[str, str, str]:
    """Extract metadata type, code body, and fullName from tool params.

    Returns:
        (metadata_type, body, full_name) — any can be empty string if not found.
    """
    metadata_type = ""
    body = ""
    full_name = ""

    if tool in ("metadata_create", "metadata_update"):
        metadata_type = params.get("type", "")
        metadata_list = params.get("metadata", [])
        if isinstance(metadata_list, list) and len(metadata_list) > 0:
            first = metadata_list[0]
            if isinstance(first, dict):
                body = first.get("body", "")
                full_name = first.get("fullName", "")

    elif tool == "tooling_api_dml":
        sobject = params.get("sObject", "")
        record = params.get("record", {})

        tooling_type_map = {
            "ApexClass": "ApexClass",
            "ApexTrigger": "ApexTrigger",
        }
        metadata_type = tooling_type_map.get(sobject, sobject)

        if isinstance(record, dict):
            body = record.get("Body", record.get("body", ""))
            full_name = record.get("Name", record.get("FullName", record.get("fullName", "")))

    return metadata_type, body, full_name


# ═══════════════════════════════════════════════════════════════════════
# ApexValidator delegation
# ═══════════════════════════════════════════════════════════════════════

def _run_apex_validator(file_path: str) -> dict[str, Any] | None:
    """Import and run the local ApexValidator. Returns None if import fails."""
    try:
        if _SCRIPT_DIR not in sys.path:
            sys.path.insert(0, _SCRIPT_DIR)
        from validate_apex import ApexValidator
        validator = ApexValidator(file_path)
        return validator.validate()
    except (ImportError, Exception):
        return None


def _basic_loop_map(body: str) -> list[bool]:
    """Return a per-line in-loop boolean list for _basic_apex_check.

    Uses paren-depth-aware character scanning — the same approach as
    validate_apex.py's _build_loop_line_map — so it correctly handles:
    - C-style for headers: for (int i = 0; i < 10; i++) — semicolons
      inside parens (paren_depth > 0) never trigger braceless-body logic
    - Braceless single-statement bodies: for (...)\n    stmt;
    - do-while with brace on same or next line: `do {` or `do\n{`
      `\bdo\b` is safe here because string literals are stripped first
    - do-while closing lines: K&R `} while (condition);` and Allman
      `while (condition);` (brace already closed on previous line) —
      the closing `}` is counted normally; "while" does NOT start a new loop
    - Non-loop braces (if/try/switch) are NOT counted as loop depth
    """
    LOOP_RE = re.compile(r"\b(?:for|while)\s*\(|\bdo\b", re.IGNORECASE)
    # Matches both K&R `} while (cond);` and Allman `while (cond);` (brace already
    # closed on the previous line). Both are do-while closings, not new loop starts.
    # The Allman alternative uses a non-backtracking balanced-paren group anchored to
    # end-of-line so it won't match a real while loop with an inline body.
    DO_WHILE_CLOSE_RE = re.compile(
        r"\}\s*while\s*\(|\bwhile\s*\([^()]*(?:\([^()]*\)[^()]*)*\)\s*;\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    # Stack of booleans: True = this brace scope was opened by a loop keyword
    brace_stack: list[bool] = []
    pending_loop = False
    paren_depth = 0
    result: list[bool] = []

    for line in body.split("\n"):
        # Strip string literals and inline comments to avoid false matches
        clean = re.sub(r"'(?:[^'\\]|\\.)*'", "''", line)
        clean = re.sub(r"//.*$", "", clean)
        clean = re.sub(r"/\*.*?\*/", "", clean)

        # Detect loop keywords; skip the "while" in "} while (...)" which
        # is the closing condition of a do-while, not a new loop start.
        if not DO_WHILE_CLOSE_RE.search(clean) and LOOP_RE.search(clean):
            pending_loop = True
            paren_depth = 0  # reset paren tracking for this loop header

        braceless_body = False
        loop_scope_opened_line = False
        for ch in clean:
            if ch == "(":
                paren_depth += 1
            elif ch == ")":
                paren_depth = max(0, paren_depth - 1)
            elif ch == "{":
                brace_stack.append(bool(pending_loop))
                if pending_loop:
                    loop_scope_opened_line = True
                pending_loop = False
            elif ch == "}":
                if brace_stack:
                    brace_stack.pop()
            elif ch == ";" and paren_depth == 0 and pending_loop:
                # Semicolon at paren-depth 0 while waiting for loop body:
                # this is a braceless single-statement body.
                braceless_body = True
                pending_loop = False

        result.append(any(brace_stack) or braceless_body or loop_scope_opened_line)

    return result


def _basic_apex_check(body: str, full_name: str) -> dict[str, Any]:
    """Fallback: basic structural checks if ApexValidator is not importable."""
    issues: list[dict[str, Any]] = []
    score = 150  # Start from ApexValidator's max

    # Check sharing keyword (@IsTest classes run in system mode — sharing is irrelevant)
    is_test_class = bool(re.search(r"@istest\b", body, re.IGNORECASE))
    if re.search(r"(public|global)\s+class", body, re.IGNORECASE) and not is_test_class:
        if not re.search(r"(with sharing|without sharing|inherited sharing)", body, re.IGNORECASE):
            issues.append({
                "severity": "WARNING",
                "category": "security",
                "message": "Class missing explicit sharing declaration",
                "line": 1,
            })
            score -= 5

    # Build in-loop map once; shared by both SOQL and DML checks
    in_loop = _basic_loop_map(body)

    # Check SOQL in loops
    for i, line in enumerate(body.split("\n"), 1):
        if in_loop[i - 1] and re.search(r"\[\s*SELECT\s+", line, re.IGNORECASE):
            issues.append({
                "severity": "CRITICAL",
                "category": "bulkification",
                "message": f"SOQL query inside loop at line {i}",
                "line": i,
            })
            score -= 10

    # Check DML in loops
    dml_patterns = [
        r"\binsert\s+", r"\bupdate\s+", r"\bdelete\s+",
        r"\bupsert\s+", r"Database\.(insert|update|delete|upsert)",
    ]
    for i, line in enumerate(body.split("\n"), 1):
        if in_loop[i - 1]:
            for dp in dml_patterns:
                if re.search(dp, line, re.IGNORECASE):
                    issues.append({
                        "severity": "CRITICAL",
                        "category": "bulkification",
                        "message": f"DML inside loop at line {i}",
                        "line": i,
                    })
                    score -= 10

    return {
        "file": full_name or "unnamed",
        "score": max(0, score),
        "max_score": 150,
        "rating": _rating(max(0, score), 150),
        "issues": issues,
        "note": "Basic fallback check — ApexValidator not available for full 150-point scoring",
    }


def _rating(score: int, max_score: int) -> str:
    """Simple rating string."""
    pct = (score / max_score * 100) if max_score > 0 else 0
    if pct >= 90:
        return "Excellent (5/5)"
    elif pct >= 80:
        return "Very Good (4/5)"
    elif pct >= 70:
        return "Good (3/5)"
    elif pct >= 60:
        return "Needs Work (2/5)"
    else:
        return "Critical Issues (1/5)"


# ═══════════════════════════════════════════════════════════════════════
# Main validation
# ═══════════════════════════════════════════════════════════════════════

def validate_apex_deployment(input_data: dict[str, Any]) -> dict[str, Any]:
    """Validate Apex code being deployed via MCP metadata tools.

    Extracts the Apex body from the metadata payload, writes it to a temp
    file, and delegates to ApexValidator (150-pt scoring).

    Args:
        input_data: Dict with "tool", "params", and optional "context".

    Returns:
        {
            "tier": "code_deployment",
            "tool": "metadata_create" | ...,
            "metadata_type": "ApexClass" | "ApexTrigger",
            "validator": "ApexValidator" | "basic_apex_check",
            "status": "scored" | "skipped" | "error",
            ... validator result fields ...
        }
    """
    tool = input_data.get("tool", "")
    params = input_data.get("params", {})

    metadata_type, body, full_name = _extract_code_body(tool, params)

    base = {
        "tier": "code_deployment",
        "tool": tool,
        "metadata_type": metadata_type,
        "full_name": full_name,
    }

    if not metadata_type:
        return {
            **base,
            "validator": None,
            "status": "error",
            "message": "Could not determine metadata type from params",
        }

    # Not an Apex type — skip
    if metadata_type not in APEX_METADATA_TYPES:
        return {
            **base,
            "validator": None,
            "status": "skipped",
            "message": f"Not an Apex metadata type ('{metadata_type}'). "
                       f"Use sf-flow for Flow validation.",
        }

    if not body or not body.strip():
        return {
            **base,
            "validator": None,
            "status": "error",
            "message": "No code body found in metadata payload",
        }

    # Write to temp file and validate
    ext = ".trigger" if metadata_type == "ApexTrigger" else ".cls"
    tmp_name = f"validate_{full_name or 'unnamed'}{ext}"
    tmp_path = os.path.join(tempfile.gettempdir(), tmp_name)

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(body)

        result = _run_apex_validator(tmp_path)
        if result is not None:
            return {**base, "validator": "ApexValidator", "status": "scored", **result}
        else:
            return {**base, "validator": "basic_apex_check", "status": "scored",
                    **_basic_apex_check(body, full_name)}
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════
# Entry point class
# ═══════════════════════════════════════════════════════════════════════

class ApexMCPValidator:
    """Validates Apex code deployments via MCP metadata tools.

    Usage:
        validator = ApexMCPValidator()
        result = validator.validate({"tool": "metadata_create", "params": {...}})
    """

    def validate(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Validate Apex deployment parameters.

        Args:
            input_data: Dict with "tool", "params", optional "context".

        Returns:
            Scored validation result.
        """
        tool = input_data.get("tool", "")

        if tool not in SUPPORTED_TOOLS:
            return {
                "tier": "code_deployment",
                "tool": tool,
                "status": "error",
                "message": f"Tool '{tool}' is not a deployment tool. "
                           f"Expected one of: {', '.join(SUPPORTED_TOOLS)}. "
                           f"For data operations, use sf-data.",
            }

        return validate_apex_deployment(input_data)
