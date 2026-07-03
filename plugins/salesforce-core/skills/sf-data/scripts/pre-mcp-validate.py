#!/usr/bin/env python3
"""
PreToolUse hook adapter for data MCP operation validation.

Fires before soql_query or sobject_dml calls.  Extracts tool parameters
from the MCP payload and validates them using the lightweight pass/fail
MCPDataValidator pipeline.

Decisions:
  - Errors (missing sObject, >200 records, bad operation) → allow with error context
  - Warnings only (PII, syntax style)                     → allow with context
  - Clean pass                                             → allow silently
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)


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

    if base_tool not in ("soql_query", "sobject_dml"):
        print(json.dumps(_allow()))
        return 0

    validator_input = {"tool": base_tool, "params": tool_input}

    try:
        from mcp_validator import MCPDataValidator

        result = MCPDataValidator().validate(validator_input)
    except (ImportError, Exception):
        # Validator unavailable — allow through silently
        print(json.dumps(_allow()))
        return 0

    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    # Errors → allow with prominent warning (never block operations)
    if errors:
        lines = [f"• {e['message']}" for e in errors[:5]]
        if len(errors) > 5:
            lines.append(f"• ...and {len(errors) - 5} more errors")

        warn_lines = [f"• {w['message']}" for w in warnings[:3]]
        warn_section = ""
        if warn_lines:
            warn_section = "\n\nWarnings:\n" + "\n".join(warn_lines)

        context = (
            f"🚨 Data operation '{base_tool}' has validation issues:\n\n"
            f"Errors:\n" + "\n".join(lines) + warn_section
        )
        print(json.dumps(_allow(context)))
        return 0

    # Warnings only → allow with context
    if warnings:
        lines = [f"• {w['message']}" for w in warnings[:5]]
        if len(warnings) > 5:
            lines.append(f"• ...and {len(warnings) - 5} more warnings")
        context = (
            f"⚠️ Data operation '{base_tool}' warnings:\n" + "\n".join(lines)
        )
        print(json.dumps(_allow(context)))
        return 0

    # Clean pass
    print(json.dumps(_allow(f"✅ Data operation '{base_tool}' validation passed")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
