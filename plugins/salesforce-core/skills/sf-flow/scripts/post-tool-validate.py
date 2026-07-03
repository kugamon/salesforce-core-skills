#!/usr/bin/env python3
"""
Post-Tool Validation Hook for sf-flow plugin.

This hook runs AFTER Write or Edit tool completes and provides validation
feedback for Salesforce Flow files (*.flow-meta.xml).

Integrates:
1. Custom 110-point scoring (6 categories)

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

# Find shared modules (../../shared relative to sf-flow)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # sf-flow/
SKILLS_ROOT = os.path.dirname(PLUGIN_ROOT)  # skills root
SHARED_DIR = os.path.join(SKILLS_ROOT, "shared")
sys.path.insert(0, SHARED_DIR)


def validate_flow(file_path: str) -> dict:
    """
    Run comprehensive Flow validation on a file.

    Args:
        file_path: Path to .flow-meta.xml file

    Returns:
        dict with validation results and output message
    """
    output_parts = []
    try:
        # ═══════════════════════════════════════════════════════════════════
        # PHASE 1: Custom 110-point validation
        # ═══════════════════════════════════════════════════════════════════
        from validate_flow import EnhancedFlowValidator

        validator = EnhancedFlowValidator(file_path)
        custom_results = validator.validate()

        flow_name = custom_results.get("flow_name", "Unknown")
        custom_score = custom_results.get("overall_score", 0)
        custom_max = 110

        # Collect issues from all categories
        custom_issues = []
        category_scores = {}

        for cat_name, cat_data in custom_results.get("categories", {}).items():
            score = cat_data.get("score", 0)
            max_score = cat_data.get("max_score", 0)
            category_scores[cat_name] = (score, max_score)

            for issue in cat_data.get("issues", []):
                custom_issues.append(
                    {
                        "severity": issue.get("severity", "INFO"),
                        "message": issue.get("message", ""),
                        "category": cat_name,
                        "fix": issue.get("fix", ""),
                    }
                )

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
        output_parts.append(f"🔄 Flow Validation: {flow_name}")
        output_parts.append("═" * 60)
        output_parts.append(f"📊 Score: {final_score}/{final_max} {stars} {rating}")

        # Category breakdown
        if category_scores:
            output_parts.append("")
            output_parts.append("📋 Category Breakdown:")
            for cat, (score, max_score) in category_scores.items():
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
            custom_issues.sort(key=lambda x: severity_order.get(x["severity"], 5))

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
                message = (
                    issue["message"][:65] + "..."
                    if len(issue["message"]) > 65
                    else issue["message"]
                )

                output_parts.append(f"   {icon} {sev}: {message}")

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
        return {"continue": True, "output": f"⚠️ Flow validator not available: {e}"}
    except Exception as e:
        return {"continue": True, "output": f"⚠️ Flow validation error: {e}"}


def main():
    """
    Main hook entry point.

    Reads hook input from stdin, validates Flow files.
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

        # Only validate Flow files
        result = {"continue": True}

        if file_path.endswith(".flow-meta.xml"):
            result = validate_flow(file_path)

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
