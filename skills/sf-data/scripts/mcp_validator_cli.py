#!/usr/bin/env python3
"""
MCP Data Validator script
========================

Command-line entry point for validating Salesforce MCP data operation parameters.

Validates soql_query and sobject_dml calls with lightweight pass/fail checks.
For code deployment validation (Apex, Flows), use sf-apex or sf-flow.

Usage:
  # JSON from stdin
  echo '{"tool":"soql_query","params":{...}}' | python mcp_validator_cli.py

  # JSON from file
  python mcp_validator_cli.py input.json

  # Human-readable report (default: JSON)
  python mcp_validator_cli.py --format report < input.json
  python mcp_validator_cli.py --format json < input.json
"""

import json
import sys
from pathlib import Path

# Ensure mcp_validator is importable from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from mcp_validator import MCPDataValidator


def format_report(result: dict) -> str:
    """Format data params result as a human-readable report."""
    lines = []

    tool = result.get("tool", "unknown")
    status = result.get("status", "unknown")
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])

    status_label = "PASS" if status == "pass" else "FAIL"

    lines.append("=" * 60)
    lines.append("  MCP Pre-Flight Check (Data Operations)")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Tool:   {tool}")
    lines.append(f"  Status: {status_label}")
    lines.append("")

    if errors:
        lines.append(f"  Errors ({len(errors)}):")
        lines.append("  " + "-" * 56)
        for err in errors:
            lines.append(f"  [ERR] {err['message']}")
        lines.append("")

    if warnings:
        lines.append(f"  Warnings ({len(warnings)}):")
        lines.append("  " + "-" * 56)
        for warn in warnings:
            lines.append(f"  [WRN] {warn['message']}")
        lines.append("")

    if not errors and not warnings:
        lines.append("  No issues found.")
        lines.append("")

    lines.append("=" * 60)

    if status == "fail":
        lines.append("  BLOCKED -- fix errors before executing")
    elif warnings:
        lines.append("  OK -- review warnings above")
    else:
        lines.append("  OK -- safe to proceed")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    """Main entry point."""
    # Parse arguments
    fmt = "json"
    input_file = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--format" and i + 1 < len(args):
            fmt = args[i + 1]
            i += 2
        elif args[i] in ("--help", "-h"):
            print(__doc__)
            sys.exit(0)
        elif not args[i].startswith("-"):
            input_file = args[i]
            i += 1
        else:
            print(f"Unknown argument: {args[i]}", file=sys.stderr)
            sys.exit(1)

    # Read input
    try:
        if input_file:
            with open(input_file, encoding="utf-8") as f:
                input_data = json.load(f)
        else:
            input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"File not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    # Validate
    validator = MCPDataValidator()
    result = validator.validate(input_data)

    # Output
    if fmt == "report":
        print(format_report(result))
    else:
        print(json.dumps(result, indent=2))

    # Exit code: 1 if fail, 0 otherwise
    sys.exit(1 if result.get("status") == "fail" else 0)


if __name__ == "__main__":
    main()
