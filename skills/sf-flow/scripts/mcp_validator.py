#!/usr/bin/env python3
"""
Flow MCP Deployment Validator
===============================

Validates Flow metadata being deployed via Salesforce MCP metadata tools.

Handles metadata_create, metadata_update, and tooling_api_dml for
Flow and FlowDefinition metadata types. Extracts the Flow XML body from
the MCP params, writes to a temp file, and delegates to the local
EnhancedFlowValidator (110-point scoring).

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
import sys
import tempfile
from typing import Any
from xml.sax.saxutils import escape as xml_escape

# ═══════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════

SUPPORTED_TOOLS = ("metadata_create", "metadata_update", "tooling_api_dml")
FLOW_METADATA_TYPES = ("Flow", "FlowDefinition")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ═══════════════════════════════════════════════════════════════════════
# Code body extraction
# ═══════════════════════════════════════════════════════════════════════

def _json_metadata_to_xml(metadata: dict[str, Any]) -> str:
    """Convert structured JSON Flow metadata to Flow XML.

    Tooling API and some metadata_create payloads send Flow definitions as
    structured JSON (e.g. {"processType": "AutoLaunchedFlow", ...}) rather
    than raw XML. This converts them to XML so EnhancedFlowValidator can
    score the flow.
    """
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<Flow xmlns="http://soap.sforce.com/2006/04/metadata">')

    # Recursively serialize JSON to XML elements
    def _serialize(obj: Any, tag: str, indent: int = 1) -> list[str]:
        prefix = "    " * indent
        result = []
        if isinstance(obj, dict):
            result.append(f"{prefix}<{tag}>")
            for key, value in obj.items():
                if isinstance(value, list):
                    for item in value:
                        result.extend(_serialize(item, key, indent + 1))
                else:
                    result.extend(_serialize(value, key, indent + 1))
            result.append(f"{prefix}</{tag}>")
        elif isinstance(obj, list):
            for item in obj:
                result.extend(_serialize(item, tag, indent))
        elif isinstance(obj, bool):
            result.append(f"{prefix}<{tag}>{'true' if obj else 'false'}</{tag}>")
        elif obj is not None:
            result.append(f"{prefix}<{tag}>{xml_escape(str(obj))}</{tag}>")
        return result

    for key, value in metadata.items():
        if isinstance(value, list):
            for item in value:
                lines.extend(_serialize(item, key))
        else:
            lines.extend(_serialize(value, key))

    lines.append("</Flow>")
    return "\n".join(lines)


def _is_structured_flow_metadata(obj: dict[str, Any]) -> bool:
    """Check if a dict looks like structured Flow metadata (JSON), not a wrapper.

    Requires ``processType`` (the key unique to Flow metadata) to avoid
    false positives on generic metadata entries that happen to have
    common keys like ``status`` or ``label``.
    """
    return "processType" in obj


def _extract_flow_body(tool: str, params: dict[str, Any]) -> tuple[str, str, str]:
    """Extract metadata type, Flow XML body, and fullName from tool params.

    Handles three formats:
    1. XML string in "body" or "content" key (metadata_create/update)
    2. Structured JSON metadata dict (tooling_api_dml with Metadata field)
    3. Structured JSON in metadata_create entries (no body/content, but has
       Flow-specific keys like processType, start, etc.)

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
                full_name = first.get("fullName", "")
                # Try explicit body/content keys first
                body = first.get("body", first.get("content", ""))
                # If no XML string found, check if the entry itself is
                # structured Flow metadata (JSON with processType, etc.)
                if not body and _is_structured_flow_metadata(first):
                    body = _json_metadata_to_xml(
                        {k: v for k, v in first.items() if k != "fullName"},
                    )

    elif tool == "tooling_api_dml":
        sobject = params.get("sObject", "")
        record = params.get("record", {})

        tooling_type_map = {
            "Flow": "Flow",
            "FlowDefinition": "FlowDefinition",
        }
        metadata_type = tooling_type_map.get(sobject, sobject)

        if isinstance(record, dict):
            body = record.get("Body", record.get("body", ""))
            full_name = record.get("FullName", record.get("fullName", ""))
            if not body:
                metadata_inner = record.get("Metadata", record.get("metadata", {}))
                if isinstance(metadata_inner, dict):
                    # Try string body/content first
                    body = metadata_inner.get("body", metadata_inner.get("content", ""))
                    # If Metadata is structured JSON (processType, start, etc.),
                    # convert to XML for validation
                    if not body and _is_structured_flow_metadata(metadata_inner):
                        body = _json_metadata_to_xml(metadata_inner)

    return metadata_type, body, full_name


# ═══════════════════════════════════════════════════════════════════════
# EnhancedFlowValidator delegation
# ═══════════════════════════════════════════════════════════════════════

def _run_flow_validator(file_path: str) -> dict[str, Any] | None:
    """Import and run the local EnhancedFlowValidator. Returns None if import fails."""
    try:
        if _SCRIPT_DIR not in sys.path:
            sys.path.insert(0, _SCRIPT_DIR)
        from validate_flow import EnhancedFlowValidator
        validator = EnhancedFlowValidator(file_path)
        return validator.validate()
    except (ImportError, Exception):
        return None


def _basic_flow_check(body: str, full_name: str) -> dict[str, Any]:
    """Fallback: basic XML structural checks if EnhancedFlowValidator is not importable."""
    issues: list[dict[str, Any]] = []
    score = 110  # Start from Flow validator's max

    # Check for description
    if "<description>" not in body:
        issues.append({
            "severity": "INFO",
            "category": "design_naming",
            "message": "Flow missing description element",
        })
        score -= 5

    # Check for DML in loops (simple string heuristic)
    has_loops = "<loops>" in body
    has_dml = any(tag in body for tag in ["<recordCreates>", "<recordUpdates>", "<recordDeletes>"])
    if has_loops and has_dml:
        issues.append({
            "severity": "WARNING",
            "category": "performance",
            "message": "Flow has both loops and DML elements — verify DML is outside loops",
        })

    # Check for fault paths on every fallible element (DML, queries, callouts,
    # waits, Apex plugin calls). A missing faultConnector on any of these can
    # silently swallow failures (screen/autolaunched flows) or block the
    # originating save (record-triggered flows). Severity HIGH so the hook
    # surfaces it prominently.
    fallible_tags = (
        "<actionCalls>",
        "<recordCreates>",
        "<recordUpdates>",
        "<recordDeletes>",
        "<recordLookups>",
        "<apexPluginCalls>",
        "<subflows>",
        "<waits>",
    )
    fallible_count = sum(body.count(tag) for tag in fallible_tags)
    fault_count = body.count("<faultConnector>")
    if fallible_count > 0 and fault_count < fallible_count:
        missing = fallible_count - fault_count
        issues.append({
            "severity": "HIGH",
            "category": "error_handling",
            "message": (
                f"{missing} fallible element(s) (actionCalls/DML/lookups/subflows/"
                f"waits/apexPluginCalls) missing faultConnector"
            ),
        })
        # 4 points per missing fault, capped at 15 of the 20 reserved for the
        # error-handling category (a single missing fault still surfaces as
        # HIGH; the cap prevents pathological inputs from zeroing the score).
        score -= min(15, missing * 4)

    return {
        "flow_name": full_name or "unnamed",
        "score": max(0, score),
        "max_score": 110,
        "rating": _rating(max(0, score), 110),
        "issues": issues,
        "note": "Basic fallback check — EnhancedFlowValidator not available for full 110-point scoring",
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

def validate_flow_deployment(input_data: dict[str, Any]) -> dict[str, Any]:
    """Validate Flow metadata being deployed via MCP metadata tools.

    Extracts the Flow XML body from the metadata payload, writes it to a
    temp file, and delegates to EnhancedFlowValidator (110-pt scoring).

    Args:
        input_data: Dict with "tool", "params", and optional "context".

    Returns:
        {
            "tier": "code_deployment",
            "tool": "metadata_create" | ...,
            "metadata_type": "Flow" | "FlowDefinition",
            "validator": "EnhancedFlowValidator" | "basic_flow_check",
            "status": "scored" | "skipped" | "error",
            ... validator result fields ...
        }
    """
    tool = input_data.get("tool", "")
    params = input_data.get("params", {})

    metadata_type, body, full_name = _extract_flow_body(tool, params)

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

    # Not a Flow type — skip
    if metadata_type not in FLOW_METADATA_TYPES:
        return {
            **base,
            "validator": None,
            "status": "skipped",
            "message": f"Not a Flow metadata type ('{metadata_type}'). "
                       f"Use sf-apex for Apex validation.",
        }

    if not body or not body.strip():
        return {
            **base,
            "validator": None,
            "status": "error",
            "message": "No Flow XML body found in metadata payload",
        }

    # Write to temp file and validate
    tmp_name = f"validate_{full_name or 'unnamed'}.flow-meta.xml"
    tmp_path = os.path.join(tempfile.gettempdir(), tmp_name)

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(body)

        result = _run_flow_validator(tmp_path)
        if result is not None:
            return {**base, "validator": "EnhancedFlowValidator", "status": "scored", **result}
        else:
            return {**base, "validator": "basic_flow_check", "status": "scored",
                    **_basic_flow_check(body, full_name)}
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════
# Entry point class
# ═══════════════════════════════════════════════════════════════════════

class FlowMCPValidator:
    """Validates Flow deployments via MCP metadata tools.

    Usage:
        validator = FlowMCPValidator()
        result = validator.validate({"tool": "metadata_create", "params": {...}})
    """

    def validate(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Validate Flow deployment parameters.

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

        return validate_flow_deployment(input_data)
