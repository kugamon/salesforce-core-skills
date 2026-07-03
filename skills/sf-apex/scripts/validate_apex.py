#!/usr/bin/env python3
"""
Apex Validator for Salesforce skills plugin.

Validates Salesforce Apex code (.cls, .trigger) for common anti-patterns
and best practice violations.

Scoring Categories (150 points total):
1. Bulkification (25 pts): SOQL/DML in loops
2. Security (25 pts): sharing settings, FLS, SOQL injection
3. Testing (25 pts): test methods, assertions, coverage
4. Architecture (20 pts): separation of concerns, patterns
5. Clean Code (20 pts): naming, complexity, comments
6. Error Handling (15 pts): try-catch, custom exceptions
7. Performance (10 pts): limits, caching, async
8. Documentation (10 pts): ApexDoc, inline comments
"""

import re
import sys
import os


class ApexValidator:
    """Validates Apex code for best practices."""

    def __init__(self, file_path: str):
        """
        Initialize the validator with an Apex file.

        Args:
            file_path: Path to .cls or .trigger file
        """
        self.file_path = file_path
        self.content = ""
        self.lines = []
        self.issues = []
        self.scores = {
            "bulkification": 25,
            "security": 25,
            "testing": 25,
            "architecture": 20,
            "clean_code": 20,
            "error_handling": 15,
            "performance": 10,
            "documentation": 10,
        }

        # Read file content
        try:
            with open(file_path, encoding="utf-8") as f:
                self.content = f.read()
                self.lines = self.content.split("\n")
        except Exception as e:
            self.issues.append(
                {
                    "severity": "CRITICAL",
                    "category": "file",
                    "message": f"Cannot read file: {e}",
                    "line": 0,
                }
            )

    def validate(self) -> dict:
        """
        Run all validations on the Apex file.

        Returns:
            Dictionary with validation results
        """
        if not self.content:
            return {
                "file": os.path.basename(self.file_path),
                "score": 0,
                "max_score": 150,
                "rating": "CRITICAL",
                "issues": self.issues,
            }

        # Build loop map once; reused by both loop checks
        self._loop_map = self._build_loop_line_map()

        # Run all checks
        self._check_soql_in_loops()
        self._check_dml_in_loops()
        self._check_security_patterns()
        self._check_null_checks()
        self._check_naming_conventions()
        self._check_error_handling()
        self._check_documentation()

        # Calculate total score
        total_score = sum(self.scores.values())

        # Determine rating
        if total_score >= 135:
            rating = "⭐⭐⭐⭐⭐ Excellent"
        elif total_score >= 112:
            rating = "⭐⭐⭐⭐ Very Good"
        elif total_score >= 90:
            rating = "⭐⭐⭐ Good"
        elif total_score >= 67:
            rating = "⭐⭐ Needs Work"
        else:
            rating = "⭐ Critical Issues"

        return {
            "file": os.path.basename(self.file_path),
            "score": total_score,
            "max_score": 150,
            "rating": rating,
            "scores": self.scores.copy(),
            "issues": self.issues,
        }

    def _build_loop_line_map(self) -> list[tuple[bool, int, bool]]:
        """Build loop context for every line in the file.

        Returns a list (one entry per line, 1-based index → result[i-1]) of
        (in_loop, loop_start_line, outer_loop_active) tuples.

        Fixes the pending_loop leak that occurs with braceless single-statement
        loop bodies (e.g. ``for (...) doSomething();``): pending_loop is cleared
        when a semicolon is encountered at parenthesis depth 0, preventing the
        next unrelated opening brace from being mis-tagged as a loop body.
        """
        # for/while set pending_loop on the keyword line and wait for a {.
        # do is included here too — do { ... } while (...) — the { may be on the
        # next line, so we treat it like for/while rather than matching do\s*{ inline.
        loop_patterns = [r"\bfor\s*\(", r"\bwhile\s*\(", r"\bdo\b"]
        # do-while closing lines: K&R `} while (cond);` and Allman `while (cond);`
        # (brace already closed on the previous line). Prevent these from being
        # treated as new loop starts. The Allman alternative uses a non-backtracking
        # balanced-paren group anchored to end-of-line so it won't match a real
        # while loop with an inline body (e.g. `while (x) stmt;`).
        DO_WHILE_CLOSE_RE = re.compile(
            r"\}\s*while\s*\(|\bwhile\s*\([^()]*(?:\([^()]*\)[^()]*)*\)\s*;\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        # Stack entries: ('loop', start_line) or ('other', start_line)
        brace_stack: list[tuple[str, int]] = []
        pending_loop = False
        loop_header_line = 0
        paren_depth = 0
        result = []

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            is_comment = stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*")

            braceless_body_line = False  # set when ';' ends a braceless loop body
            loop_scope_opened_line = False  # set when a loop scope opens on this line
            # Capture outer loop context BEFORE this line potentially starts a new loop.
            # Used to distinguish a standalone for-each (outer_loop_active=False) from
            # one that is nested inside an enclosing loop (outer_loop_active=True).
            outer_loop_active = any(t == "loop" for t, _ in brace_stack)

            if not is_comment:
                # Strip string literals first so that // inside strings (e.g.
                # 'https://api.com') is not mis-treated as a comment marker.
                # Then strip inline comments so that } inside comments (e.g.
                # `for (...) { // }`) cannot prematurely pop brace_stack.
                line_for_patterns = re.sub(r"'(?:[^'\\]|\\.)*'", "''", line)
                line_for_patterns = re.sub(r"//.*$", "", line_for_patterns)
                line_for_patterns = re.sub(r"/\*.*?\*/", "", line_for_patterns)
                if (not DO_WHILE_CLOSE_RE.search(line_for_patterns) and
                        any(re.search(p, line_for_patterns, re.IGNORECASE) for p in loop_patterns)):
                    pending_loop = True
                    loop_header_line = i
                    paren_depth = 0  # reset for this loop header

                for char in line_for_patterns:
                    if char == "(":
                        paren_depth += 1
                    elif char == ")":
                        paren_depth = max(0, paren_depth - 1)
                    elif char == "{":
                        if pending_loop:
                            brace_stack.append(("loop", loop_header_line))
                            loop_scope_opened_line = True
                            pending_loop = False
                        else:
                            brace_stack.append(("other", i))
                    elif char == "}":
                        if brace_stack:
                            brace_stack.pop()
                    elif char == ";" and paren_depth == 0 and pending_loop:
                        # Semicolon outside parens while waiting for loop body brace:
                        # braceless single-statement body — this line IS inside the loop.
                        braceless_body_line = True
                        pending_loop = False

            in_loop = (
                any(t == "loop" for t, _ in brace_stack)
                or braceless_body_line
                or loop_scope_opened_line
            )
            loop_start = next(
                (ln for t, ln in brace_stack if t == "loop"),
                loop_header_line if (braceless_body_line or loop_scope_opened_line) else 0,
            )
            result.append((in_loop, loop_start, outer_loop_active))

        return result

    def _check_soql_in_loops(self):
        """Check for SOQL queries inside loops (critical anti-pattern)."""
        soql_pattern = r"\[\s*SELECT\s+"
        # for-each over SOQL result: for (Type var : [SELECT...]) — the SOQL is the
        # iterable, not inside the body; this is the correct bulkified pattern.
        foreach_soql_pattern = r"\bfor\s*\([^:]+:\s*\["
        loop_map = self._loop_map

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                continue
            in_loop, loop_start, outer_loop_active = loop_map[i - 1]
            if in_loop and re.search(soql_pattern, line, re.IGNORECASE):
                # Exempt standalone for-each-over-SOQL only when NOT nested in an outer
                # loop. When outer_loop_active is True, the for-each is inside an
                # enclosing loop, so the SOQL IS executed per outer iteration — a real
                # governor-limit risk that must not be silently skipped.
                if re.search(foreach_soql_pattern, line, re.IGNORECASE) and not outer_loop_active:
                    continue
                self.issues.append(
                    {
                        "severity": "CRITICAL",
                        "category": "bulkification",
                        "message": f"SOQL query inside loop (loop started line {loop_start})",
                        "line": i,
                        "fix": "Move SOQL before loop, query all needed records, filter in loop",
                    }
                )
                self.scores["bulkification"] -= 10

    def _check_dml_in_loops(self):
        """Check for DML operations inside loops (critical anti-pattern)."""
        dml_patterns = [
            r"\binsert\s+",
            r"\bupdate\s+",
            r"\bdelete\s+",
            r"\bupsert\s+",
            r"\bundelete\s+",
            r"Database\.(insert|update|delete|upsert)",
        ]
        loop_map = self._loop_map

        for i, line in enumerate(self.lines, 1):
            # Skip comment lines (avoids false positives from words like "update" in JavaDoc)
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                continue
            in_loop, loop_start, _outer = loop_map[i - 1]
            if in_loop:
                for dml_pattern in dml_patterns:
                    if re.search(dml_pattern, line, re.IGNORECASE):
                        self.issues.append(
                            {
                                "severity": "CRITICAL",
                                "category": "bulkification",
                                "message": f"DML inside loop (loop started line {loop_start})",
                                "line": i,
                                "fix": "Collect records in loop, perform single DML after loop",
                            }
                        )
                        self.scores["bulkification"] -= 10

    def _check_security_patterns(self):
        """Check for security-related patterns."""
        # Pattern handles optional modifiers (e.g. "with sharing", "virtual", "abstract")
        # between the access modifier and the "class" keyword.
        class_decl_pattern = r"\b(public|private|global)\b.*?\bclass\s+\w+"
        sharing_pattern = r"\b(with\s+sharing|without\s+sharing|inherited\s+sharing)\b"

        # @IsTest classes run in system mode and do not require sharing declarations.
        # Check if the file-level @IsTest annotation is present (before the first class).
        is_test_class = bool(re.search(r"@istest\b", self.content, re.IGNORECASE))

        # Collect all class declarations: (line_num, has_sharing, is_without_sharing)
        class_declarations = []

        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                continue
            if re.search(class_decl_pattern, line, re.IGNORECASE):
                has_sharing = bool(re.search(sharing_pattern, line, re.IGNORECASE))
                is_without = bool(re.search(r"\bwithout\s+sharing\b", line, re.IGNORECASE))
                class_declarations.append((i, has_sharing, is_without))

        if class_declarations:
            # Outer class (first declaration) must have an explicit sharing keyword
            # Exception: @IsTest classes run in system mode — sharing is irrelevant
            outer_line, outer_has_sharing, outer_is_without = class_declarations[0]
            if not outer_has_sharing and not is_test_class:
                self.issues.append(
                    {
                        "severity": "WARNING",
                        "category": "security",
                        "message": "Class missing explicit sharing declaration",
                        "line": outer_line,
                        "fix": 'Add "with sharing" (recommended) or "inherited sharing" to class declaration',
                    }
                )
                self.scores["security"] -= 5
            elif outer_is_without:
                self.issues.append(
                    {
                        "severity": "WARNING",
                        "category": "security",
                        "message": 'Class uses "without sharing" - ensure this is intentional',
                        "line": outer_line,
                        "fix": 'Use "with sharing" by default, "inherited sharing" for utilities',
                    }
                )
                self.scores["security"] -= 5

            # Inner classes inherit sharing from the outer class — only flag "without sharing"
            for line_num, _has_sharing, is_without in class_declarations[1:]:
                if is_without:
                    self.issues.append(
                        {
                            "severity": "WARNING",
                            "category": "security",
                            "message": 'Inner class uses "without sharing" - ensure this is intentional',
                            "line": line_num,
                            "fix": "Inner classes inherit sharing from the outer class by default",
                        }
                    )
                    self.scores["security"] -= 5

        # Check for SOQL injection vulnerability
        dynamic_soql_pattern = r"Database\.query\s*\("
        for i, line in enumerate(self.lines, 1):
            if re.search(dynamic_soql_pattern, line):
                # Check if using String.escapeSingleQuotes
                if "escapeSingleQuotes" not in self.content:
                    self.issues.append(
                        {
                            "severity": "WARNING",
                            "category": "security",
                            "message": "Dynamic SOQL without evident escape - potential injection risk",
                            "line": i,
                            "fix": "Use String.escapeSingleQuotes() or bind variables",
                        }
                    )
                    self.scores["security"] -= 5

    def _check_null_checks(self):
        """Check for missing null checks before method calls."""
        # Full static analysis requires an AST; this is a placeholder for
        # future implementation.
        pass

    def _check_naming_conventions(self):
        """Check for naming convention violations."""
        # Class names should be PascalCase
        # Match actual class declarations (with optional modifiers), not "class" in comments
        class_pattern = r"^\s*(?:public|private|global|virtual|abstract|with\s+sharing|without\s+sharing|\s)*\s*class\s+(\w+)"
        for i, line in enumerate(self.lines, 1):
            # Skip comment lines
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                continue
            match = re.search(class_pattern, line, re.IGNORECASE)
            if match:
                class_name = match.group(1)
                if not class_name[0].isupper():
                    self.issues.append(
                        {
                            "severity": "INFO",
                            "category": "clean_code",
                            "message": f'Class name "{class_name}" should be PascalCase',
                            "line": i,
                        }
                    )
                    self.scores["clean_code"] -= 2

        # Method names should be camelCase
        method_pattern = r"(public|private|protected|global)\s+(static\s+)?(\w+)\s+(\w+)\s*\("
        for i, line in enumerate(self.lines, 1):
            match = re.search(method_pattern, line)
            if match:
                method_name = match.group(4)
                # Skip constructors and test methods
                if method_name[0].isupper() and "@isTest" not in "\n".join(self.lines[:i - 1]):
                    if method_name not in [
                        m.group(1) for m in re.finditer(class_pattern, self.content)
                    ]:
                        self.issues.append(
                            {
                                "severity": "INFO",
                                "category": "clean_code",
                                "message": f'Method name "{method_name}" should be camelCase',
                                "line": i,
                            }
                        )
                        self.scores["clean_code"] -= 2

    def _check_error_handling(self):
        """Check for error handling patterns."""
        # Check for empty catch blocks
        empty_catch_pattern = r"catch\s*\([^)]+\)\s*\{\s*\}"
        for i, line in enumerate(self.lines, 1):
            if re.search(empty_catch_pattern, line):
                self.issues.append(
                    {
                        "severity": "WARNING",
                        "category": "error_handling",
                        "message": "Empty catch block - exceptions are silently swallowed",
                        "line": i,
                        "fix": "Log the exception or handle it appropriately",
                    }
                )
                self.scores["error_handling"] -= 5

        # Check for generic exception catch without specific handling
        if "catch (Exception e)" in self.content:
            # This is OK as a fallback, but should have specific catches first
            pass

    def _check_documentation(self):
        """Check for documentation/comments."""
        # Check for ApexDoc on public methods
        public_method_pattern = r"public\s+(\w+)\s+(\w+)\s*\("

        for i, line in enumerate(self.lines, 1):
            if re.search(public_method_pattern, line):
                # Check if there's a comment/ApexDoc before this line
                has_doc = False
                if i > 1:
                    prev_lines = "\n".join(self.lines[max(0, i - 5) : i - 1])
                    if "/**" in prev_lines or "//" in prev_lines:
                        has_doc = True

                if not has_doc:
                    self.issues.append(
                        {
                            "severity": "INFO",
                            "category": "documentation",
                            "message": "Public method missing documentation",
                            "line": i,
                            "fix": "Add ApexDoc comment: /** @description ... */",
                        }
                    )
                    self.scores["documentation"] -= 2


def main():
    """Command-line interface for Apex validation."""
    if len(sys.argv) < 2:
        print("Usage: python validate_apex.py <file.cls|file.trigger>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    validator = ApexValidator(file_path)
    results = validator.validate()

    # Print results
    print(f"\n🔍 Apex Validation: {results['file']}")
    print(f"Score: {results['score']}/{results['max_score']} {results['rating']}")
    print()

    if results["issues"]:
        print("Issues found:")
        for issue in results["issues"]:
            severity_icon = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}.get(
                issue["severity"], "⚪"
            )
            print(
                f"  {severity_icon} [{issue['severity']}] Line {issue['line']}: {issue['message']}"
            )
            if "fix" in issue:
                print(f"      Fix: {issue['fix']}")
    else:
        print("✅ No issues found!")

    # Return non-zero if critical issues
    critical_count = sum(1 for i in results["issues"] if i["severity"] == "CRITICAL")
    sys.exit(1 if critical_count > 0 else 0)


if __name__ == "__main__":
    main()
