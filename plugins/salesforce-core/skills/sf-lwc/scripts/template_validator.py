#!/usr/bin/env python3
"""
LWC Template Anti-Pattern Validator.

Detects common mistakes that LLMs make when generating LWC templates:
1. Inline JavaScript expressions ({a + b})
2. Ternary operators in templates ({x ? a : b})
3. Object/array literals in attributes
4. Method calls in templates ({items.length})
5. Comparison operators in if:true
6. Event handlers with inline arguments

This validator is ADVISORY - it provides warnings but does not block operations.

Source: https://salesforcediaries.com/2026/01/16/llm-mistakes-in-apex-lwc-salesforce-code-generation-rules/
"""

import re
import os


class LWCTemplateValidator:
    """Detects LLM-specific anti-patterns in LWC HTML templates."""

    # Patterns for inline expressions (arithmetic, concatenation)
    INLINE_EXPRESSION_PATTERNS = [
        # Arithmetic operations
        (
            r"\{[^}]*\s*[\+\-\*\/]\s*[^}]*\}",
            "Arithmetic expression",
            "Use a getter in your JS file",
        ),
        # Ternary operators
        (
            r"\{[^}]*\s*\?\s*[^}]+\s*:\s*[^}]*\}",
            "Ternary operator",
            "Use a getter or if:true/if:false",
        ),
        # String concatenation with +
        (
            r"\{[^}]*['\"]\s*\+\s*[^}]*\}",
            "String concatenation",
            "Use a getter with template literals",
        ),
        # Template literals (backticks)
        (r"\{`[^`]*`\}", "Template literal", "Template literals not supported; use getter"),
    ]

    # Patterns for method calls in templates
    METHOD_CALL_PATTERNS = [
        # .method() call
        (
            r"\{[^}]*\.\w+\s*\(\s*[^)]*\)\s*[^}]*\}",
            "Method call",
            "Use a getter instead of calling methods",
        ),
        # .length, .size, etc. (common array/string properties that need getters)
        (
            r"\{[^}]*\.length[^}]*\}",
            "Array/string .length",
            "Use a getter: get count() { return this.items.length; }",
        ),
        (r"\{[^}]*\.size[^}]*\}", "Collection .size", "Use a getter"),
        # Common method patterns
        (r"\{[^}]*\.toUpperCase\s*\(\)", "toUpperCase()", "Use a getter"),
        (r"\{[^}]*\.toLowerCase\s*\(\)", "toLowerCase()", "Use a getter"),
        (r"\{[^}]*\.trim\s*\(\)", "trim()", "Use a getter"),
        (r"\{[^}]*\.toString\s*\(\)", "toString()", "Use a getter"),
        (r"\{[^}]*\.join\s*\(", "join()", "Use a getter"),
        (r"\{[^}]*\.slice\s*\(", "slice()", "Use a getter"),
        (r"\{[^}]*\.split\s*\(", "split()", "Use a getter"),
        (r"\{[^}]*\.filter\s*\(", "filter()", "Use a getter"),
        (r"\{[^}]*\.map\s*\(", "map()", "Use a getter"),
        (r"\{[^}]*\.find\s*\(", "find()", "Use a getter"),
        (r"\{[^}]*\.includes\s*\(", "includes()", "Use a getter"),
        (r"\{[^}]*JSON\.stringify\s*\(", "JSON.stringify()", "Use a getter"),
        (r"\{[^}]*JSON\.parse\s*\(", "JSON.parse()", "Use a getter"),
    ]

    # Patterns for comparisons in if:true/if:false
    COMPARISON_PATTERNS = [
        # Comparison operators in if:true
        (
            r"if:true=\{[^}]*\s*[><=!]+\s*[^}]*\}",
            "Comparison in if:true",
            "Use a getter: get isGreater() { return x > 5; }",
        ),
        (r"if:false=\{[^}]*\s*[><=!]+\s*[^}]*\}", "Comparison in if:false", "Use a getter"),
        # Logical operators
        (
            r"if:true=\{[^}]*\s*&&\s*[^}]*\}",
            "Logical AND in if:true",
            "Use a getter: get bothTrue() { return a && b; }",
        ),
        (r"if:false=\{[^}]*\s*&&\s*[^}]*\}", "Logical AND in if:false", "Use a getter"),
        (r"if:true=\{[^}]*\s*\|\|\s*[^}]*\}", "Logical OR in if:true", "Use a getter"),
        (r"if:false=\{[^}]*\s*\|\|\s*[^}]*\}", "Logical OR in if:false", "Use a getter"),
        # Negation
        (r"if:true=\{!\w", "Negation in if:true", "Use if:false instead, or use a getter"),
    ]

    # Patterns for object/array literals
    LITERAL_PATTERNS = [
        # Object literal in attribute
        (
            r"=\{\s*\{[^}]+\}\s*\}",
            "Inline object literal",
            "Define objects in your JS file as properties",
        ),
        # Array literal in attribute
        (
            r"=\{\s*\[[^\]]+\]\s*\}",
            "Inline array literal",
            "Define arrays in your JS file as properties",
        ),
    ]

    # Patterns for incorrect event handler syntax
    EVENT_HANDLER_PATTERNS = [
        # Event handler with parentheses/arguments
        (
            r"on\w+=\{[\w.]+\s*\([^)]+\)\s*\}",
            "Event handler with arguments",
            "Use data-* attributes instead",
        ),
        # Arrow function in handler
        (
            r"on\w+=\{\s*\([^)]*\)\s*=>",
            "Arrow function in handler",
            "Define handler method in JS, use data-* for context",
        ),
        # .bind() in handler
        (
            r"on\w+=\{[\w.]+\.bind\s*\(",
            ".bind() in handler",
            "Use data-* attributes for context instead",
        ),
    ]

    # Patterns for common Vue/React/Angular syntax mistakes
    FRAMEWORK_SYNTAX_PATTERNS = [
        # Vue v-model / v-bind / v-on
        (r"\bv-model\s*=", "Vue v-model syntax", "LWC uses value={prop} with onchange handler"),
        (r"\bv-bind:", "Vue v-bind syntax", "LWC uses {property} binding"),
        (r"\bv-on:", "Vue v-on syntax", "LWC uses on* handlers (onclick, onchange)"),
        (r"\bv-if\s*=", "Vue v-if syntax", "LWC uses if:true={condition}"),
        (r"\bv-for\s*=", "Vue v-for syntax", 'LWC uses for:each={array} for:item="item"'),
        (r"\bv-show\s*=", "Vue v-show syntax", "LWC uses if:true/if:false or CSS classes"),
        # React patterns
        (r"\bclassName\s*=", "React className", "LWC uses class={classString}"),
        (r"\bhtmlFor\s*=", "React htmlFor", "LWC uses for attribute or lightning-input label"),
        (
            r"\bonClick\s*=\s*\{[^}]*\(\s*\)",
            "React onClick with call",
            "LWC uses onclick={handler} without parentheses",
        ),
        # Angular patterns
        (r"\[\(ngModel\)\]", "Angular two-way binding", "LWC uses value={prop} with onchange"),
        (r"\*ngIf\s*=", "Angular *ngIf", "LWC uses if:true={condition}"),
        (r"\*ngFor\s*=", "Angular *ngFor", 'LWC uses for:each={array} for:item="item"'),
        (r"\(click\)\s*=", "Angular event binding", "LWC uses onclick={handler}"),
    ]

    # Missing key in iteration
    ITERATION_PATTERNS = [
        (
            r'for:each=\{[^}]+\}\s+for:item="[^"]+"\s*>',
            "for:each without key",
            "Add key={item.id} to the first child element",
        ),
    ]

    def __init__(self, file_path: str):
        """
        Initialize the validator with an LWC HTML file.

        Args:
            file_path: Path to .html file
        """
        self.file_path = file_path
        self.content = ""
        self.lines = []
        self.issues = []

        try:
            with open(file_path, encoding="utf-8") as f:
                self.content = f.read()
                self.lines = self.content.split("\n")
        except Exception as e:
            self.issues.append(
                {
                    "severity": "ERROR",
                    "category": "file",
                    "message": f"Cannot read file: {e}",
                    "line": 0,
                }
            )

    def validate(self) -> dict:
        """
        Run all LWC template validations.

        Returns:
            Dictionary with validation results
        """
        if not self.content:
            return {
                "file": os.path.basename(self.file_path),
                "issues": self.issues,
                "issue_count": len(self.issues),
            }

        # Run all checks
        self._check_patterns(self.INLINE_EXPRESSION_PATTERNS, "inline_expression", "CRITICAL")
        self._check_patterns(self.METHOD_CALL_PATTERNS, "method_call", "CRITICAL")
        self._check_patterns(self.COMPARISON_PATTERNS, "comparison", "CRITICAL")
        self._check_patterns(self.LITERAL_PATTERNS, "literal", "CRITICAL")
        self._check_patterns(self.EVENT_HANDLER_PATTERNS, "event_handler", "WARNING")
        self._check_patterns(self.FRAMEWORK_SYNTAX_PATTERNS, "framework_syntax", "CRITICAL")
        self._check_iteration_keys()

        return {
            "file": os.path.basename(self.file_path),
            "issues": self.issues,
            "issue_count": len(self.issues),
        }

    def _check_patterns(self, patterns: list, category: str, severity: str):
        """Check for pattern matches in the template."""
        for i, line in enumerate(self.lines, 1):
            # Skip HTML comments
            if "<!--" in line and "-->" in line:
                continue

            for pattern, name, fix in patterns:
                matches = re.finditer(pattern, line)
                for _match in matches:
                    # Avoid duplicate issues for same line/category
                    existing = any(
                        issue["line"] == i
                        and issue["category"] == category
                        and name in issue["message"]
                        for issue in self.issues
                    )
                    if not existing:
                        self.issues.append(
                            {
                                "severity": severity,
                                "category": category,
                                "message": f"{name} not supported in LWC templates",
                                "line": i,
                                "fix": fix,
                                "source": "template-validator",
                            }
                        )

    def _check_iteration_keys(self):
        """Check for missing key attribute in for:each iterations."""
        in_foreach = False
        foreach_line = 0
        foreach_item = ""

        for i, line in enumerate(self.lines, 1):
            # Detect for:each start
            foreach_match = re.search(r'for:each=\{([^}]+)\}\s+for:item="([^"]+)"', line)
            if foreach_match:
                foreach_line = i
                foreach_item = foreach_match.group(2)

                # If key is present on the same line, no warning is needed.
                if "key=" in line or "key =" in line:
                    in_foreach = False
                    continue

                # Single-line iteration blocks can close on the same line.
                if ">" in line and "</" in line:
                    self.issues.append(
                        {
                            "severity": "WARNING",
                            "category": "iteration",
                            "message": f"for:each iteration (line {foreach_line}) may be missing key attribute",
                            "line": i,
                            "fix": f"Add key={{{foreach_item}.id}} to identify each item uniquely",
                            "source": "template-validator",
                        }
                    )
                    in_foreach = False
                    continue

                in_foreach = True
                continue

            if in_foreach:
                # Look for key attribute in the next few lines
                if "key=" in line or "key =" in line:
                    in_foreach = False
                    continue

                # If we hit a closing tag or another element without key
                if ">" in line and not line.strip().startswith("<!--"):
                    # Check if it's a template tag (doesn't need key directly)
                    if "<template" not in line:
                        self.issues.append(
                            {
                                "severity": "WARNING",
                                "category": "iteration",
                                "message": f"for:each iteration (line {foreach_line}) may be missing key attribute",
                                "line": i,
                                "fix": f"Add key={{{foreach_item}.id}} to identify each item uniquely",
                                "source": "template-validator",
                            }
                        )
                    in_foreach = False


def validate_lwc_template(file_path: str) -> dict:
    """
    Validate an LWC HTML template for anti-patterns.

    Args:
        file_path: Path to .html file

    Returns:
        Dictionary with validation results
    """
    validator = LWCTemplateValidator(file_path)
    return validator.validate()


def format_output(results: dict) -> str:
    """Format validation results for display."""
    issues = results.get("issues", [])

    if not issues:
        return ""

    output_parts = []
    output_parts.append("")
    output_parts.append(f"🔍 LWC Template Check: {results['file']}")
    output_parts.append("─" * 50)

    # Group by severity
    critical = [i for i in issues if i["severity"] == "CRITICAL"]
    warnings = [i for i in issues if i["severity"] == "WARNING"]

    if critical:
        output_parts.append(f"🔴 Critical ({len(critical)}):")
        for issue in critical[:5]:
            output_parts.append(f"   L{issue['line']}: {issue['message']}")
            if issue.get("fix"):
                fix = issue["fix"][:60] + "..." if len(issue["fix"]) > 60 else issue["fix"]
                output_parts.append(f"      💡 {fix}")

    if warnings:
        output_parts.append(f"🟡 Warnings ({len(warnings)}):")
        for issue in warnings[:3]:
            output_parts.append(f"   L{issue['line']}: {issue['message']}")
            if issue.get("fix"):
                fix = issue["fix"][:60] + "..." if len(issue["fix"]) > 60 else issue["fix"]
                output_parts.append(f"      💡 {fix}")

    remaining = len(issues) - len(critical[:5]) - len(warnings[:3])
    if remaining > 0:
        output_parts.append(f"   ... and {remaining} more issues")

    output_parts.append("─" * 50)
    output_parts.append("📚 See: sf-lwc/docs/template-anti-patterns.md")

    return "\n".join(output_parts)


def _read_stdin_hook_input(timeout_seconds: float = 5.0) -> str:
    """Read hook JSON from stdin WITHOUT hanging forever.

    Previous behavior: any non-tty stdin (e.g. a subprocess pipe with nothing
    written to it) caused json.load(sys.stdin) to block indefinitely. Now we
    wait at most `timeout_seconds` for data and fail explicitly otherwise.
    Returns the file_path extracted from the hook payload, or "".
    """
    import sys
    import json

    try:
        import select

        ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
        if not ready:
            return ""
    except (ImportError, OSError, ValueError):
        # select unavailable (e.g. some Windows pipes) — fall through and
        # attempt the read; the explicit CLI path below is preferred anyway.
        pass

    try:
        hook_input = json.load(sys.stdin)
        return hook_input.get("tool_input", {}).get("file_path", "") or ""
    except (json.JSONDecodeError, EOFError, ValueError):
        return ""


if __name__ == "__main__":
    import sys

    file_path = None
    cli_mode = False

    # Mode 1 (preferred): CLI mode - file path from command-line argument.
    # Checked FIRST so that `python template_validator.py file.html` never
    # touches stdin (the old stdin-first order hung when stdin was an idle pipe).
    args = [a for a in sys.argv[1:] if a != "--stdin"]
    if args:
        file_path = args[0]
        cli_mode = True

    # Mode 2: Hook mode - read JSON payload from stdin (bounded wait, never hangs)
    if not file_path and not sys.stdin.isatty():
        file_path = _read_stdin_hook_input()
        if not file_path:
            print(
                "Error: no file argument given and no hook JSON arrived on stdin "
                "within 5s. Pass the template path as an argument: "
                "python template_validator.py <component.html>",
                file=sys.stderr,
            )
            sys.exit(2)

    # No file path from either mode
    if not file_path:
        print("Usage: python template_validator.py <component.html>")
        print('   Or: echo \'{"tool_input": {"file_path": "..."}}\' | python template_validator.py')
        sys.exit(2)

    # Scope filter: hook mode stays silent (advisory, never blocks the tool);
    # CLI mode reports explicitly instead of exiting silently.
    if not file_path.endswith(".html"):
        if cli_mode:
            print(f"Skipped: {file_path} is not an .html LWC template", file=sys.stderr)
            sys.exit(2)
        sys.exit(0)
    if "/lwc/" not in file_path.replace(os.sep, "/") and not cli_mode:
        sys.exit(0)

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    results = validate_lwc_template(file_path)

    # Print formatted output
    output = format_output(results)
    if output:
        print(output)
    else:
        print(f"✅ No template anti-patterns detected in {results['file']}")

    sys.exit(0)  # Advisory only - don't block
