#!/usr/bin/env python3
"""
PreToolUse hook adapter for metadata MCP deployment validation.

Fires before metadata_create, metadata_update, or tooling_api_dml calls
targeting supported metadata types (CustomObject, CustomField, ValidationRule,
RecordType, PermissionSet).

Runs the MetadataOperationValidator scoring pipeline and converts results
to hook decisions.

Decisions:
  - Critical issues (schema/required-field failures)  → allow with critical warning
  - Score < 67%                                       → allow with warning
  - Pass                                              → allow with score summary
  - Unsupported type or validator unavailable          → allow silently
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

THRESHOLD_PCT = 67  # advisory warning below this percentage


def _allow(context: str = "") -> dict:
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
    if context:
        out["hookSpecificOutput"]["additionalContext"] = context
    return out


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        print(json.dumps(_allow()))
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Strip mcp__<server>__ prefix → base tool name.
    parts = tool_name.split("__", 2)
    base_tool = parts[2] if tool_name.startswith("mcp__") and len(parts) > 2 else tool_name

    validator_input = {"tool": base_tool, "params": tool_input}

    try:
        from mcp_validator import MetadataMCPValidator

        result = MetadataMCPValidator().validate(validator_input)
    except (ImportError, Exception):
        print(json.dumps(_allow()))
        return 0

    status = result.get("status", "")

    # Not a supported metadata type — skip
    if status in ("skipped", "error"):
        print(json.dumps(_allow()))
        return 0

    # Scored result
    score = result.get("score", 0)
    max_score = result.get("max_score", 1)
    full_name = result.get("full_name", "metadata")
    metadata_type = result.get("metadata_type", "")
    categories = result.get("categories", {})

    pct = (score / max_score * 100) if max_score > 0 else 0

    # Collect all issues from categories
    all_issues = []
    for cat in categories.values():
        if isinstance(cat, dict):
            all_issues.extend(cat.get("issues", []))

    # Critical issues → allow with prominent warning (never block)
    critical = [i for i in all_issues if i.get("severity") == "critical"]
    if critical:
        lines = [f"• {i['message']}" for i in critical[:5]]
        if len(critical) > 5:
            lines.append(f"• ...and {len(critical) - 5} more critical issues")

        context = (
            f"🚨 Metadata validation found critical issues for "
            f"'{metadata_type}:{full_name}' "
            f"(score: {score}/{max_score}, {pct:.0f}%).\n\n"
            f"Critical issues to fix:\n"
            + "\n".join(lines)
        )
        print(json.dumps(_allow(context)))
        return 0

    # Below threshold — allow with advisory warning
    if pct < THRESHOLD_PCT:
        warnings = [i for i in all_issues if i.get("severity") == "warning"]
        top = warnings[:4]
        issue_lines = [f"• {i['message']}" for i in top]
        if len(warnings) > 4:
            issue_lines.append(f"• ...and {len(warnings) - 4} more issues")
        summary = "\n".join(issue_lines)

        context = (
            f"⚠️ Metadata score below threshold for "
            f"'{metadata_type}:{full_name}': "
            f"{score}/{max_score} ({pct:.0f}% — threshold is {THRESHOLD_PCT}%). "
            f"Consider fixing before deploying:\n{summary}"
        )
        print(json.dumps(_allow(context)))
        return 0

    # Pass — allow with score summary
    if pct >= 90:
        stars = "⭐⭐⭐⭐⭐"
    elif pct >= 75:
        stars = "⭐⭐⭐⭐"
    else:
        stars = "⭐⭐⭐"

    label = f"{metadata_type}:{full_name}" if metadata_type else full_name
    print(json.dumps(_allow(f"✅ Metadata validation passed for '{label}': {score}/{max_score} {stars}")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
