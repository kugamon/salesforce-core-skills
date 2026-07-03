#!/usr/bin/env python3
"""
Flow Validation CLI

Standalone on-demand validation of a local Flow file.
Runs the 110-point EnhancedFlowValidator pipeline and prints a scored
report to stdout.

Usage:
  python3 validate_flow_cli.py path/to/Auto_Lead_Assignment.flow-meta.xml
  python3 validate_flow_cli.py path/to/MyFlow.xml
  python3 validate_flow_cli.py path/to/flow_metadata.json

Accepts both XML (.flow-meta.xml) and JSON (metadata_read output) formats.
JSON files with a "processType" key are automatically converted to XML
before validation.

Exit codes:
  0  — validation passed (score >= 80%)
  1  — validation failed (score < 80%) or file not found
"""

import json
import os
import sys
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

THRESHOLD_PCT = 80
MAX_SCORE = 110


def _prepare_flow_file(file_path: str) -> str:
    """Prepare a Flow file for validation, converting JSON to XML if needed.

    Returns path to an XML file suitable for EnhancedFlowValidator.
    The caller must clean up any temp file created.
    """
    with open(file_path, encoding="utf-8") as f:
        content = f.read().strip()

    # Detect JSON input (metadata_read returns JSON for Flows)
    if content.startswith("{"):
        try:
            data = json.loads(content)
            # Check if it looks like Flow metadata (has processType)
            if "processType" in data:
                from mcp_validator import _json_metadata_to_xml

                # Strip wrapper keys that aren't part of Flow XML
                flow_data = {k: v for k, v in data.items() if k not in ("fullName", "fileName")}
                xml_content = _json_metadata_to_xml(flow_data)
                tmp_path = os.path.join(
                    tempfile.gettempdir(),
                    os.path.basename(file_path).rsplit(".", 1)[0] + ".flow-meta.xml",
                )
                with open(tmp_path, "w", encoding="utf-8") as f:
                    f.write(xml_content)
                return tmp_path
        except (json.JSONDecodeError, KeyError):
            pass  # Not valid JSON or not Flow metadata — try as XML

    return file_path  # Already XML


def run_validation(file_path: str) -> dict:
    """Run full validation pipeline on a Flow file (XML or JSON).

    Returns a dict with keys: success, output, score, max_score, pct.
    """
    output_parts = []
    converted_path = None

    try:
        from validate_flow import EnhancedFlowValidator

        # Convert JSON to XML if needed
        actual_path = _prepare_flow_file(file_path)
        if actual_path != file_path:
            converted_path = actual_path  # Track for cleanup

        validator = EnhancedFlowValidator(actual_path)
        results = validator.validate()

        flow_name = results.get("flow_name", os.path.basename(file_path))
        score = results.get("overall_score", 0)
        max_score = MAX_SCORE
        categories = results.get("categories", {})

        # Collect all issues from top-level aggregated lists.
        # EnhancedFlowValidator category dicts use critical_issues/warnings/advisory keys,
        # NOT a generic "issues" key — iterating cat_data.get("issues") would always be empty.
        # The top-level critical_issues and warnings lists are pre-aggregated by validate().
        issues = []
        for item in results.get("critical_issues", []):
            issues.append({
                "severity": item.get("severity", "CRITICAL"),
                "category": "",
                "message": item.get("message", ""),
                "line": 0,
                "fix": item.get("fix", ""),
            })
        for item in results.get("warnings", []):
            issues.append({
                "severity": item.get("severity", "HIGH"),
                "category": "",
                "message": item.get("message", ""),
                "line": 0,
                "fix": item.get("suggestion", ""),
            })
        for item in results.get("advisory_suggestions", []):
            issues.append({
                "severity": "INFO",
                "category": "",
                "message": item if isinstance(item, str) else item.get("message", ""),
                "line": 0,
                "fix": "" if isinstance(item, str) else item.get("suggestion", ""),
            })

        pct = (score / max_score * 100) if max_score > 0 else 0

        if pct >= 90:
            rating_stars, rating = 5, "Excellent"
        elif pct >= 75:
            rating_stars, rating = 4, "Very Good"
        elif pct >= 60:
            rating_stars, rating = 3, "Good"
        elif pct >= 45:
            rating_stars, rating = 2, "Needs Work"
        else:
            rating_stars, rating = 1, "Critical Issues"

        stars = "⭐" * rating_stars + "☆" * (5 - rating_stars)

        output_parts.append("")
        output_parts.append(f"🔄 Flow Validation: {flow_name}")
        output_parts.append("═" * 60)
        output_parts.append(f"📊 Score: {score}/{max_score} {stars} {rating}")

        if categories:
            output_parts.append("")
            output_parts.append("📋 Category Breakdown:")
            for cat_name, cat_data in categories.items():
                cat_score = cat_data.get("score", 0)
                cat_max = cat_data.get("max_score", 0)
                if cat_max > 0:
                    icon = "✅" if cat_score == cat_max else ("⚠️" if cat_score >= cat_max * 0.7 else "❌")
                    diff = f" (-{cat_max - cat_score})" if cat_score < cat_max else ""
                    display = cat_name.replace("_", " ").title()
                    output_parts.append(f"   {icon} {display}: {cat_score}/{cat_max}{diff}")

        if issues:
            output_parts.append("")
            output_parts.append(f"⚠️  Issues Found ({len(issues)}):")
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "MODERATE": 3, "WARNING": 4, "LOW": 5, "INFO": 6}
            issues.sort(key=lambda x: severity_order.get(x.get("severity", "INFO"), 6))
            for issue in issues[:12]:
                sev = issue.get("severity", "INFO")
                icon = {
                    "CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡",
                    "MODERATE": "🟡", "WARNING": "🟡", "LOW": "🔵", "INFO": "⚪",
                }.get(sev, "⚪")
                line_info = f"L{issue['line']}" if issue.get("line") else ""
                msg = issue["message"][:65] + "..." if len(issue["message"]) > 65 else issue["message"]
                output_parts.append(f"   {icon} {sev} {line_info}: {msg}")
                if issue.get("fix"):
                    fix = issue["fix"][:55] + "..." if len(issue["fix"]) > 55 else issue["fix"]
                    output_parts.append(f"      💡 Fix: {fix}")
            if len(issues) > 12:
                output_parts.append(f"   ... and {len(issues) - 12} more issues")
        else:
            output_parts.append("")
            output_parts.append("✅ No issues found!")

        output_parts.append("═" * 60)
        if pct >= THRESHOLD_PCT:
            output_parts.append("✅ PASSED — safe to deploy")
        else:
            output_parts.append("❌ BELOW THRESHOLD — fix issues before deploying")

        return {"success": True, "output": "\n".join(output_parts), "score": score, "max_score": max_score, "pct": pct}

    except ImportError as e:
        return {"success": False, "output": f"⚠️  Validator not available: {e}", "pct": 0}
    except Exception as e:
        return {"success": False, "output": f"⚠️  Validation error: {e}", "pct": 0}
    finally:
        # Clean up temp file created by JSON→XML conversion
        if converted_path:
            try:
                os.remove(converted_path)
            except OSError:
                pass


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: validate_flow_cli.py <file.flow-meta.xml|file.xml|file.json>", file=sys.stderr)
        return 1

    file_path = args[0]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}", file=sys.stderr)
        return 1

    result = run_validation(file_path)
    print(result["output"])
    return 0 if result.get("success") and result.get("pct", 0) >= THRESHOLD_PCT else 1


if __name__ == "__main__":
    sys.exit(main())
