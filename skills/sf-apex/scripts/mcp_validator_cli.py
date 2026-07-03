#!/usr/bin/env python3
"""
Apex MCP Validator script
========================

Command-line entry point for validating Apex code deployments via Salesforce MCP.

Validates metadata_create, metadata_update, and tooling_api_dml calls
for ApexClass and ApexTrigger types with 150-point scoring.

Usage:
  # JSON from stdin
  echo '{"tool":"metadata_create","params":{...}}' | python mcp_validator_cli.py

  # JSON from file
  python mcp_validator_cli.py input.json

  # Human-readable report (default: JSON)
  python mcp_validator_cli.py --format report < input.json
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mcp_validator import ApexMCPValidator


def format_report(result: dict) -> str:
    """Format Apex deployment validation result as a human-readable report."""
    lines = []

    tool = result.get("tool", "unknown")
    metadata_type = result.get("metadata_type", "unknown")
    full_name = result.get("full_name", "")
    validator = result.get("validator", "none")
    status = result.get("status", "unknown")

    lines.append("=" * 60)
    lines.append("  Apex MCP Deployment Validation")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"  Tool:          {tool}")
    lines.append(f"  Metadata Type: {metadata_type}")
    if full_name:
        lines.append(f"  Full Name:     {full_name}")
    lines.append(f"  Validator:     {validator}")
    lines.append(f"  Status:        {status}")
    lines.append("")

    if status == "skipped":
        lines.append(f"  {result.get('message', 'Skipped')}")
        lines.append("")
    elif status == "error":
        lines.append(f"  Error: {result.get('message', 'Unknown error')}")
        lines.append("")
    elif status == "scored":
        score = result.get("score", result.get("overall_score", 0))
        max_score = result.get("max_score", result.get("total_max", 0))
        rating = result.get("rating", "")

        lines.append(f"  Score:  {score}/{max_score}")
        lines.append(f"  Rating: {rating}")
        lines.append("")

        issues = result.get("issues", [])
        critical_issues = result.get("critical_issues", [])
        all_issues = critical_issues + issues

        if all_issues:
            lines.append("  Issues:")
            lines.append("  " + "-" * 56)
            for issue in all_issues[:15]:
                severity = issue.get("severity", "INFO")
                message = issue.get("message", "Unknown")
                icon = "ERR" if severity in ("CRITICAL", "error") else "WRN" if severity in ("WARNING", "warning") else "INF"
                line_num = issue.get("line", "")
                loc = f" (line {line_num})" if line_num else ""
                lines.append(f"  [{icon}] {message}{loc}")
            if len(all_issues) > 15:
                lines.append(f"  ... and {len(all_issues) - 15} more")
            lines.append("")

        note = result.get("note", "")
        if note:
            lines.append(f"  Note: {note}")
            lines.append("")

    lines.append("=" * 60)

    if status == "scored":
        score = result.get("score", result.get("overall_score", 0))
        max_score = result.get("max_score", result.get("total_max", 150))
        critical = result.get("critical_issues", [])
        pct = (score / max_score * 100) if max_score > 0 else 0
        if critical:
            lines.append("  BLOCKED -- fix critical issues before deploying")
        elif pct >= 70:
            lines.append("  PASSED -- safe to deploy")
        else:
            lines.append("  REVIEW -- address issues before deploying")
    elif status == "skipped":
        lines.append("  SKIPPED -- not an Apex deployment")
    else:
        lines.append(f"  STATUS: {status}")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    """Main entry point."""
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

    validator = ApexMCPValidator()
    result = validator.validate(input_data)

    if fmt == "report":
        print(format_report(result))
    else:
        print(json.dumps(result, indent=2))

    # Exit code
    if result.get("status") == "error":
        sys.exit(1)
    if result.get("status") == "scored":
        critical = result.get("critical_issues", [])
        if critical:
            sys.exit(1)
        score = result.get("score", result.get("overall_score", 0))
        max_score = result.get("max_score", result.get("total_max", 150))
        pct = (score / max_score * 100) if max_score > 0 else 0
        sys.exit(1 if pct < 50 else 0)
    sys.exit(0)


if __name__ == "__main__":
    main()
