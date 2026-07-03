#!/usr/bin/env python3
"""
PreToolUse hook adapter for Flow MCP deployment validation.

Fires before metadata_create, metadata_update, or tooling_api_dml calls.
Extracts the Flow XML body from the MCP payload and validates it using
the 110-point EnhancedFlowValidator.

Decisions:
  - CRITICAL/HIGH issues (DML in loops, missing fault paths)  → allow with critical warning
  - Score < 80% (< 88/110)                                    → allow with warning
  - Pass                                                       → allow with score summary
  - Non-Flow type or validator unavailable                     → allow silently
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

THRESHOLD_PCT = 80  # block advisory below this percentage
MAX_SCORE = 110


def _allow(context: str = "") -> dict:
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
    if context:
        out["hookSpecificOutput"]["additionalContext"] = context
    return out


def _collect_issues(result: dict) -> list:
    """Collect all issues from validator result.

    Handles both EnhancedFlowValidator (top-level critical_issues/warnings/advisory_suggestions lists)
    and basic_flow_check (top-level issues list) formats.
    EnhancedFlowValidator category dicts use critical_issues/warnings/advisory keys,
    NOT a generic "issues" key — iterating cat_data.get("issues") would always be empty.
    """
    issues = list(result.get("issues", []))  # basic_flow_check format
    for item in result.get("critical_issues", []):
        issues.append({
            "severity": item.get("severity", "CRITICAL"),
            "message": item.get("message", ""),
            "line": 0,
        })
    for item in result.get("warnings", []):
        issues.append({
            "severity": item.get("severity", "HIGH"),
            "message": item.get("message", ""),
            "line": 0,
        })
    for item in result.get("advisory_suggestions", []):
        issues.append({
            "severity": "INFO",
            "message": item if isinstance(item, str) else item.get("message", ""),
            "line": 0,
        })
    return issues


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        print(json.dumps(_allow()))
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Strip mcp__<server>__  prefix → base tool name.
    # Server names may contain underscores (e.g. mcp__salesforce__metadata_create),
    # so split on __ with maxsplit=2 rather than using a character-class regex.
    parts = tool_name.split("__", 2)
    base_tool = parts[2] if tool_name.startswith("mcp__") and len(parts) > 2 else tool_name

    validator_input = {"tool": base_tool, "params": tool_input}

    try:
        from mcp_validator import FlowMCPValidator

        result = FlowMCPValidator().validate(validator_input)
    except (ImportError, Exception):
        # Validator unavailable — allow through silently
        print(json.dumps(_allow()))
        return 0

    status = result.get("status", "")

    # Not a Flow type — skip
    if status in ("skipped", "error"):
        print(json.dumps(_allow()))
        return 0

    # Scored result
    score = result.get("score", result.get("overall_score", 0))
    max_score = result.get("max_score", MAX_SCORE)
    full_name = result.get("full_name", result.get("flow_name", "flow"))
    all_issues = _collect_issues(result)
    pct = (score / max_score * 100) if max_score > 0 else 0

    # Critical/High issues → allow with prominent warning (never block)
    blocking = [i for i in all_issues if i.get("severity") in ("CRITICAL", "HIGH")]
    if blocking:
        lines = []
        for issue in blocking[:5]:
            loc = f" (line {issue['line']})" if issue.get("line") else ""
            lines.append(f"• {issue['message']}{loc}")
        if len(blocking) > 5:
            lines.append(f"• ...and {len(blocking) - 5} more critical issues")

        context = (
            f"🚨 Flow validation found critical issues for '{full_name}' "
            f"(score: {score}/{max_score}, {pct:.0f}%).\n\n"
            f"Critical issues to fix:\n"
            + "\n".join(lines)
        )
        print(json.dumps(_allow(context)))
        return 0

    # Below threshold — allow with advisory warning
    if pct < THRESHOLD_PCT:
        top = all_issues[:4]
        issue_lines = [f"• {i['message']}" for i in top]
        if len(all_issues) > 4:
            issue_lines.append(f"• ...and {len(all_issues) - 4} more issues")
        summary = "\n".join(issue_lines)

        context = (
            f"⚠️ Flow score below threshold for '{full_name}': "
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

    print(json.dumps(_allow(f"✅ Flow validation passed for '{full_name}': {score}/{max_score} {stars}")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
