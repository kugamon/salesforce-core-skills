#!/usr/bin/env python3
"""
Apex Validation script

Standalone on-demand validation of a local Apex file.
Runs the same 150-point + LLM anti-pattern pipeline as the PostToolUse hook
and prints a scored report to stdout.

Usage:
  python3 validate_apex_cli.py path/to/MyClass.cls
  python3 validate_apex_cli.py path/to/AccountTrigger.trigger

Exit codes:
  0  — validation passed (score >= 67%)
  1  — validation failed (score < 67%) or file not found
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

THRESHOLD_PCT = 67


def run_validation(file_path: str) -> dict:
    """Run full validation pipeline on an Apex file.

    Returns a dict with keys: success, output, score, max_score, pct.
    """
    output_parts = []

    try:
        from validate_apex import ApexValidator

        validator = ApexValidator(file_path)
        max_scores = dict(validator.scores)  # capture before validate() mutates in place
        results = validator.validate()

        score = results.get("score", 0)
        max_score = results.get("max_score", 150)
        issues = list(results.get("issues", []))
        scores = results.get("scores", {})

        # LLM anti-pattern check
        try:
            from llm_pattern_validator import LLMPatternValidator

            llm_results = LLMPatternValidator(file_path).validate()
            for issue in llm_results.get("issues", []):
                issues.append(
                    {
                        "severity": issue.get("severity", "WARNING"),
                        "category": issue.get("category", "llm_pattern"),
                        "message": issue.get("message", ""),
                        "line": issue.get("line", 0),
                        "fix": issue.get("fix", ""),
                        "source": "llm-validator",
                    }
                )
        except Exception:
            pass

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
        output_parts.append(f"🔍 Apex Validation: {os.path.basename(file_path)}")
        output_parts.append("═" * 60)
        output_parts.append(f"📊 Score: {score}/{max_score} {stars} {rating}")

        if scores:
            output_parts.append("")
            output_parts.append("📋 Category Breakdown:")
            for cat, cat_score in scores.items():
                max_cat = max_scores.get(cat, 0)
                if max_cat > 0:
                    icon = "✅" if cat_score == max_cat else ("⚠️" if cat_score >= max_cat * 0.7 else "❌")
                    diff = f" (-{max_cat - cat_score})" if cat_score < max_cat else ""
                    display = cat.replace("_", " ").title()
                    output_parts.append(f"   {icon} {display}: {cat_score}/{max_cat}{diff}")

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
                source = f"[{issue['source']}] " if issue.get("source") else ""
                line_info = f"L{issue['line']}" if issue.get("line") else ""
                msg = issue["message"][:65] + "..." if len(issue["message"]) > 65 else issue["message"]
                output_parts.append(f"   {icon} {sev} {source}{line_info}: {msg}")
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


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: validate_apex_cli.py <file.cls|file.trigger>", file=sys.stderr)
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
