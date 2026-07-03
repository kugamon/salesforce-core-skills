#!/usr/bin/env python3
"""
Post-Tool Validation Hook for sf-apex plugin.

This hook runs AFTER Write or Edit tool completes and provides validation
feedback for Salesforce Apex files (*.cls, *.trigger).

Integrates:
1. Custom 150-point scoring (8 categories)
2. LLM pattern validation (Java types, hallucinated methods)

Hook Input (stdin): JSON with tool_input and tool_response
Hook Output (stdout): JSON with optional output message

This hook is ADVISORY - it provides feedback but does not block operations.
"""

import sys
import os
import json

# Add script directory to path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Find shared modules (../../shared relative to sf-apex)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # sf-apex/
SKILLS_ROOT = os.path.dirname(PLUGIN_ROOT)  # skills root
SHARED_DIR = os.path.join(SKILLS_ROOT, "shared")
sys.path.insert(0, SHARED_DIR)


def validate_apex(file_path: str) -> dict:
    """
    Run comprehensive Apex validation on a file.

    Args:
        file_path: Path to .cls or .trigger file

    Returns:
        dict with validation results and output message
    """
    output_parts = []

    try:
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1: Custom 150-point validation
        # ═══════════════════════════════════════════════════════════════════
        from validate_apex import ApexValidator

        validator = ApexValidator(file_path)
        custom_results = validator.validate()

        custom_score = custom_results.get("score", 0)
        custom_max = custom_results.get("max_score", 150)
        custom_issues = custom_results.get("issues", [])
        custom_scores = custom_results.get("scores", {})

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1.5: LLM Pattern Validation (Java types, hallucinated methods)
        # ═══════════════════════════════════════════════════════════════════
        try:
            from llm_pattern_validator import LLMPatternValidator

            llm_validator = LLMPatternValidator(file_path)
            llm_results = llm_validator.validate()
            llm_issues = llm_results.get("issues", [])

            # Add LLM issues to custom_issues with adjusted severity
            for issue in llm_issues:
                custom_issues.append(
                    {
                        "severity": issue.get("severity", "WARNING"),
                        "category": issue.get("category", "llm_pattern"),
                        "message": issue.get("message", ""),
                        "line": issue.get("line", 0),
                        "fix": issue.get("fix", ""),
                        "source": "llm-validator",
                    }
                )
        except ImportError:
            pass  # LLM validator not available
        except Exception:
            pass  # Don't fail validation on LLM check errors

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 2: Calculate rating
        # ═══════════════════════════════════════════════════════════════════
        final_score = custom_score
        final_max = custom_max

        pct = (final_score / final_max * 100) if final_max > 0 else 0
        if pct >= 90:
            rating_stars = 5
            rating = "Excellent"
        elif pct >= 75:
            rating_stars = 4
            rating = "Very Good"
        elif pct >= 60:
            rating_stars = 3
            rating = "Good"
        elif pct >= 45:
            rating_stars = 2
            rating = "Needs Work"
        else:
            rating_stars = 1
            rating = "Critical Issues"

        # ═══════════════════════════════════════════════════════════════════
        # PHASE 3: Format output
        # ═══════════════════════════════════════════════════════════════════
        stars = "⭐" * rating_stars + "☆" * (5 - rating_stars)

        output_parts.append("")
        output_parts.append(f"🔍 Apex Validation: {os.path.basename(file_path)}")
        output_parts.append("═" * 60)
        output_parts.append(f"📊 Score: {final_score}/{final_max} {stars} {rating}")

        # Category breakdown
        if custom_scores:
            output_parts.append("")
            output_parts.append("📋 Category Breakdown:")
            for cat, score in custom_scores.items():
                max_score = validator.scores.get(cat, 0)
                if max_score > 0:
                    icon = "✅" if score == max_score else ("⚠️" if score >= max_score * 0.7 else "❌")
                    diff = f" (-{max_score - score})" if score < max_score else ""
                    display_name = cat.replace("_", " ").title()
                    output_parts.append(f"   {icon} {display_name}: {score}/{max_score}{diff}")

        # Issues list
        if custom_issues:
            output_parts.append("")
            output_parts.append(f"⚠️ Issues Found ({len(custom_issues)}):")

            # Sort by severity
            severity_order = {
                "CRITICAL": 0,
                "HIGH": 1,
                "MODERATE": 2,
                "WARNING": 3,
                "LOW": 4,
                "INFO": 5,
            }
            custom_issues.sort(key=lambda x: severity_order.get(x.get("severity", "INFO"), 5))

            # Display up to 12 issues
            for issue in custom_issues[:12]:
                sev = issue.get("severity", "INFO")
                icon = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠",
                    "MODERATE": "🟡",
                    "WARNING": "🟡",
                    "LOW": "🔵",
                    "INFO": "⚪",
                }.get(sev, "⚪")
                source = f"[{issue['source']}] " if issue.get("source") else ""
                line_info = f"L{issue['line']}" if issue.get("line") else ""
                message = (
                    issue["message"][:65] + "..."
                    if len(issue["message"]) > 65
                    else issue["message"]
                )

                output_parts.append(
                    f"   {icon} {sev} {source}{line_info}: {message}"
                )

                if issue.get("fix"):
                    fix = issue["fix"][:55] + "..." if len(issue["fix"]) > 55 else issue["fix"]
                    output_parts.append(f"      💡 Fix: {fix}")

            if len(custom_issues) > 12:
                output_parts.append(f"   ... and {len(custom_issues) - 12} more issues")
        else:
            output_parts.append("")
            output_parts.append("✅ No issues found!")

        output_parts.append("═" * 60)

        return {"continue": True, "output": "\n".join(output_parts)}

    except ImportError as e:
        return {"continue": True, "output": f"⚠️ Apex validator not available: {e}"}
    except Exception as e:
        return {"continue": True, "output": f"⚠️ Apex validation error: {e}"}


def main():
    """
    Main hook entry point.

    Reads hook input from stdin, validates Apex files.
    """
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin)

        # Extract file path from tool input
        tool_input = hook_input.get("tool_input", {})
        file_path = tool_input.get("file_path", "")

        # Check if operation was successful
        tool_response = hook_input.get("tool_response", {})
        if not tool_response.get("success", True):
            # Operation failed, don't validate
            print(json.dumps({"continue": True}))
            return 0

        # Only validate Apex files
        result = {"continue": True}

        if file_path.endswith(".cls") or file_path.endswith(".trigger"):
            result = validate_apex(file_path)

        # Output result
        print(json.dumps(result))
        return 0

    except json.JSONDecodeError:
        # No valid JSON input, continue silently
        print(json.dumps({"continue": True}))
        return 0
    except Exception as e:
        # Unexpected error, log but don't block
        print(json.dumps({"continue": True, "output": f"⚠️ Hook error: {e}"}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
