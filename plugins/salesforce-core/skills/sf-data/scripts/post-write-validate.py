#!/usr/bin/env python3
"""
sf-data Post-Write Validation Hook (LEGACY)
=============================================

NOTE: This hook validates LOCAL files (.apex, .soql, .csv, .json) written to disk.
In Salesforce MCP workflows, operations go directly to the org — no local files are
written. For MCP pre-flight validation, use mcp_validator_cli.py instead:

    echo '{"tool":"sobject_dml","params":{...}}' | python mcp_validator_cli.py

This hook is retained for backward compatibility with local template validation.
It is ADVISORY — it provides feedback but does not block writes.
"""

import json
import sys
from pathlib import Path

# Add shared modules path
SCRIPT_DIR = Path(__file__).parent
PLUGIN_ROOT = SCRIPT_DIR.parent.parent  # sf-data/
SKILLS_ROOT = PLUGIN_ROOT.parent  # skills/
SHARED_DIR = SKILLS_ROOT / "shared"
sys.path.insert(0, str(SHARED_DIR))


def main():
    """Main entry point for the validation hook."""
    try:
        # Read tool input from stdin
        input_data = json.load(sys.stdin)

        tool_input = input_data.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        if not file_path:
            # No file path provided, skip validation
            return

        # Determine file type and validate
        path = Path(file_path)
        extension = path.suffix.lower()

        # Only validate data-related files
        if extension not in [".apex", ".soql", ".csv", ".json"]:
            return

        # Check if file is in sf-data templates or user's data scripts
        if not is_data_file(file_path):
            return

        # Import the appropriate validator
        script_dir = Path(__file__).parent
        sys.path.insert(0, str(script_dir))

        from validate_data_operation import DataOperationValidator

        # Run validation
        validator = DataOperationValidator(file_path)
        result = validator.validate()

        # Output validation report
        if result:
            output = {"output": format_validation_report(result)}
            print(json.dumps(output))

    except Exception as e:
        # Log error but don't block the write
        error_output = {"output": f"Validation skipped: {str(e)}"}
        print(json.dumps(error_output))


def is_data_file(file_path: str) -> bool:
    """Check if the file is a data operation file that should be validated."""
    path = Path(file_path)

    # Check if it's in sf-data templates
    if "sf-data" in str(path) and "templates" in str(path):
        return True

    # Check if it's a data script based on naming patterns
    name_lower = path.stem.lower()
    data_patterns = [
        "factory",
        "bulk",
        "insert",
        "update",
        "delete",
        "upsert",
        "import",
        "export",
        "cleanup",
        "test",
        "data",
        "query",
    ]

    for pattern in data_patterns:
        if pattern in name_lower:
            return True

    # Check file extension for SOQL files
    if path.suffix.lower() == ".soql":
        return True

    return False


def format_validation_report(result: dict) -> str:
    """Format the validation result as a readable report."""
    lines = []

    # Header
    score = result.get("score", 0)
    max_score = result.get("max_score", 130)
    rating = get_rating(score, max_score)

    lines.append("=" * 60)
    lines.append("   sf-data Validation Report (Legacy File Validator)")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Score: {score}/{max_score} {rating}")
    lines.append("")

    # Category breakdown
    categories = result.get("categories", {})
    if categories:
        lines.append("Category Breakdown:")
        lines.append("-" * 60)
        for cat_name, cat_data in categories.items():
            cat_score = cat_data.get("score", 0)
            cat_max = cat_data.get("max", 0)
            pct = (cat_score / cat_max * 100) if cat_max > 0 else 0
            status = "OK" if pct >= 80 else "!!" if pct >= 60 else "XX"
            lines.append(f"[{status}] {cat_name}: {cat_score}/{cat_max} ({pct:.0f}%)")
        lines.append("")

    # Issues
    issues = result.get("issues", [])
    if issues:
        lines.append("Issues Found:")
        lines.append("-" * 60)
        for issue in issues[:10]:
            severity = issue.get("severity", "warning")
            icon = "ERR" if severity == "error" else "WRN"
            message = issue.get("message", "Unknown issue")
            lines.append(f"[{icon}] {message}")
        if len(issues) > 10:
            lines.append(f"   ... and {len(issues) - 10} more issues")
        lines.append("")

    # Recommendations
    recommendations = result.get("recommendations", [])
    if recommendations:
        lines.append("Recommendations:")
        lines.append("-" * 60)
        for rec in recommendations[:5]:
            lines.append(f"-> {rec}")
        lines.append("")

    lines.append("=" * 60)

    # Status
    if score >= max_score * 0.9:
        lines.append("VALIDATION PASSED - Excellent!")
    elif score >= max_score * 0.7:
        lines.append("VALIDATION PASSED - Good")
    elif score >= max_score * 0.5:
        lines.append("VALIDATION PASSED - Review recommended")
    else:
        lines.append("VALIDATION PASSED (Advisory) - Please review issues")

    lines.append("=" * 60)

    return "\n".join(lines)


def get_rating(score: int, max_score: int) -> str:
    """Get star rating based on score percentage."""
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


if __name__ == "__main__":
    main()
