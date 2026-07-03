#!/usr/bin/env python3
"""
PreToolUse hook adapter for LWC MCP deployment validation.

Fires before metadata_create, metadata_update, or tooling_api_dml calls
targeting LightningComponentBundle.  Extracts the payload from the MCP
parameters and validates it using the SLDS + template analysis pipeline.

Decisions:
  - Validation error (empty bundle, etc.)   → allow with error context
  - Critical template issues                → allow with critical warning
  - Score < 67%                             → allow with warning
  - Pass                                    → allow with score summary
  - Non-LWC type or validator unavailable   → allow silently
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
        from mcp_validator import LWCMCPValidator

        result = LWCMCPValidator().validate(validator_input)
    except (ImportError, Exception):
        print(json.dumps(_allow()))
        return 0

    status = result.get("status", "")

    # Not an LWC type — skip
    if status == "skipped":
        print(json.dumps(_allow()))
        return 0

    # Validation error (e.g. empty bundle, unsupported tool) — allow with context
    if status == "error":
        message = result.get("message", "LWC validation error")
        print(json.dumps(_allow(f"🚨 LWC validation error: {message}")))
        return 0

    # Scored result
    score = result.get("score", 0)
    max_score = result.get("max_score", 1)
    full_name = result.get("full_name", "component")
    issues = result.get("issues", [])
    pct = (score / max_score * 100) if max_score > 0 else 0

    # Critical issues → allow with prominent warning (never block)
    critical = [i for i in issues if i.get("severity") == "CRITICAL"]
    if critical:
        lines = [f"• {i['message']}" for i in critical[:5]]
        if len(critical) > 5:
            lines.append(f"• ...and {len(critical) - 5} more critical issues")

        context = (
            f"🚨 LWC validation found critical issues for '{full_name}' "
            f"(score: {score}/{max_score}, {pct:.0f}%).\n\n"
            f"Critical issues to fix:\n"
            + "\n".join(lines)
        )
        print(json.dumps(_allow(context)))
        return 0

    # Below threshold — allow with advisory warning
    if pct < THRESHOLD_PCT:
        warnings = [i for i in issues if i.get("severity") == "WARNING"]
        top = warnings[:4]
        issue_lines = [f"• {i['message']}" for i in top]
        if len(warnings) > 4:
            issue_lines.append(f"• ...and {len(warnings) - 4} more issues")
        summary = "\n".join(issue_lines)

        context = (
            f"⚠️ LWC score below threshold for '{full_name}': "
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

    print(json.dumps(_allow(f"✅ LWC validation passed for '{full_name}': {score}/{max_score} {stars}")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
