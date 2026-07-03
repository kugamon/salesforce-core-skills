#!/usr/bin/env python3
"""Salesforce metadata payload validator with lightweight 120-point scoring."""

from __future__ import annotations

import re
from typing import Any

CATEGORIES = {
    "schema": 20,
    "naming": 20,
    "security": 20,
    "documentation": 20,
    "deployability": 20,
    "maintainability": 20,
}
MAX_SCORE = sum(CATEGORIES.values())

SUPPORTED_METADATA_TYPES = {
    "CustomObject",
    "CustomField",
    "ValidationRule",
    "RecordType",
    "PermissionSet",
    "FlexiPage",
    "Layout",
}

# FlexiPage constants discovered from live org testing.
FLEXIPAGE_VALID_TYPES = {
    "AppPage",
    "RecordPage",
    "HomePage",
    "ObjectPage",
    "ForecastingPage",
    "MailAppAppPage",
    "CommAppPage",
    "UtilityBar",
    "EmbeddedServicePage",
}

FLEXIPAGE_TEMPLATES = {
    "RecordPage": "flexipage:recordHomeTemplateDesktop",
    "AppPage": "flexipage:defaultAppHomeTemplate",
    "HomePage": "home:desktopTemplate",
}

# Visibility rules only support the EQUAL operator in FlexiPage metadata.
FLEXIPAGE_VISIBILITY_OPERATORS = {"EQUAL"}

LAYOUT_SECTION_STYLES = {
    "TwoColumnsTopToBottom",
    "TwoColumnsLeftToRight",
    "OneColumn",
    "CustomLinks",
}

LAYOUT_ITEM_BEHAVIORS = {"Edit", "Required", "Readonly"}


class MetadataOperationValidator:
    """Score a single Salesforce metadata payload."""

    def __init__(self, metadata_type: str, payload: dict[str, Any]):
        self.metadata_type = metadata_type
        self.payload = payload
        self.categories = {k: {"max": v, "score": v, "issues": []} for k, v in CATEGORIES.items()}
        self.issues: list[dict[str, Any]] = []

    def validate(self) -> dict[str, Any]:
        if self.metadata_type not in SUPPORTED_METADATA_TYPES:
            self._deduct("schema", 20, f"Unsupported metadata type: {self.metadata_type}", "critical")
            return self._result()

        if not isinstance(self.payload, dict) or not self.payload:
            self._deduct("schema", 20, "Metadata payload is missing or empty", "critical")
            return self._result()

        self._check_required_fields()
        self._check_naming()
        self._check_security()
        self._check_documentation()
        self._check_deployability()
        self._check_maintainability()

        return self._result()

    def _check_required_fields(self):
        required_by_type = {
            "CustomObject": ("fullName", "label", "nameField", "deploymentStatus", "sharingModel"),
            "CustomField": ("fullName", "label", "type"),
            "ValidationRule": ("fullName", "active", "errorConditionFormula", "errorMessage"),
            "RecordType": ("fullName", "label", "active"),
            "PermissionSet": ("fullName", "label"),
            "FlexiPage": ("masterLabel", "type", "template"),
            "Layout": (),
        }
        for key in required_by_type.get(self.metadata_type, ()):
            if key not in self.payload:
                self._deduct("schema", 5, f"Missing required field '{key}'", "critical")

        # FlexiPage-specific schema checks.
        if self.metadata_type == "FlexiPage":
            self._check_flexipage_schema()

        # Layout-specific schema checks.
        if self.metadata_type == "Layout":
            self._check_layout_schema()

    def _check_naming(self):
        full_name = str(self.payload.get("fullName", ""))

        # FlexiPage uses masterLabel instead of fullName for display.
        if self.metadata_type == "FlexiPage":
            master_label = str(self.payload.get("masterLabel", ""))
            if not master_label.strip():
                self._deduct("naming", 6, "masterLabel should not be blank", "critical")
            return

        # Layout naming is handled by the sObject-LayoutName convention.
        if self.metadata_type == "Layout":
            return

        if not full_name:
            return

        if self.metadata_type in {"CustomObject", "CustomField"} and "__" not in full_name:
            self._deduct("naming", 8, "Custom metadata fullName should use Salesforce suffixes (for example __c)", "warning")

        if re.search(r"\s", full_name):
            self._deduct("naming", 6, "fullName should not contain whitespace", "critical")

    def _check_security(self):
        # ValidationRule formula scanning for fragile syntax patterns.
        if self.metadata_type == "ValidationRule":
            formula = str(self.payload.get("errorConditionFormula", ""))
            formula_findings = analyze_formula_safety(formula)
            for finding in formula_findings:
                self._deduct("security", 5, finding, "warning")

        # PermissionSet should avoid granting ModifyAllData by default.
        if self.metadata_type == "PermissionSet":
            if self.payload.get("hasModifyAllData") is True:
                self._deduct("security", 10, "PermissionSet grants ModifyAllData; verify least-privilege intent", "critical")

    def _check_documentation(self):
        description = self.payload.get("description")
        if not isinstance(description, str) or not description.strip():
            self._deduct("documentation", 4, "Description is missing or empty", "warning")

        # Layout sections should have labels for readability.
        if self.metadata_type == "Layout":
            sections = self.payload.get("layoutSections", [])
            if isinstance(sections, list):
                unlabeled = sum(1 for s in sections if isinstance(s, dict) and not s.get("label"))
                if unlabeled > 0:
                    self._deduct("documentation", 3, f"{unlabeled} layout section(s) missing labels", "warning")

    def _check_deployability(self):
        if self.metadata_type == "CustomObject" and "deploymentStatus" in self.payload:
            if self.payload["deploymentStatus"] not in {"Deployed", "InDevelopment"}:
                self._deduct("deployability", 8, "deploymentStatus should be Deployed or InDevelopment", "critical")

        # FlexiPage visibility-rule operators are checked in _check_flexipage_visibility_rules.
        # Additional deployability: RecordPage without regions is undeployable.
        if self.metadata_type == "FlexiPage":
            regions = self.payload.get("flexiPageRegions", [])
            if not isinstance(regions, list) or len(regions) == 0:
                self._deduct("deployability", 8, "FlexiPage has no regions; at least one is required", "critical")

    def _check_maintainability(self):
        if self.metadata_type == "ValidationRule":
            formula = str(self.payload.get("errorConditionFormula", ""))
            if len(formula) > 250:
                self._deduct("maintainability", 6, "Validation rule formula is long; consider splitting logic", "warning")

        if self.metadata_type == "FlexiPage":
            regions = self.payload.get("flexiPageRegions", [])
            if isinstance(regions, list) and len(regions) > 10:
                self._deduct("maintainability", 4, "FlexiPage has many regions; consider simplifying layout", "warning")

    def _check_flexipage_schema(self):
        """Validate FlexiPage-specific structure."""
        fp_type = self.payload.get("type", "")
        if fp_type and fp_type not in FLEXIPAGE_VALID_TYPES:
            self._deduct("schema", 8, f"FlexiPage type '{fp_type}' is not a recognized page type", "critical")

        # RecordPage must have sobjectType.
        if fp_type == "RecordPage" and not self.payload.get("sobjectType"):
            self._deduct("schema", 5, "RecordPage requires 'sobjectType'", "critical")

        # AppPage and HomePage should NOT have sobjectType.
        if fp_type in ("AppPage", "HomePage") and self.payload.get("sobjectType"):
            self._deduct("schema", 3, f"{fp_type} should not have 'sobjectType'", "warning")

        # Validate template name.
        template = self.payload.get("template")
        if isinstance(template, dict):
            tpl_name = template.get("name", "")
            expected = FLEXIPAGE_TEMPLATES.get(fp_type)
            if expected and tpl_name and tpl_name != expected:
                self._deduct(
                    "schema", 4,
                    f"Template '{tpl_name}' may not work for {fp_type}; expected '{expected}'",
                    "warning",
                )

        # Validate component names in regions.
        self._check_flexipage_components()

        # Validate visibility rule operators.
        self._check_flexipage_visibility_rules()

    def _check_flexipage_components(self):
        """Warn about unrecognized component names."""
        regions = self.payload.get("flexiPageRegions", [])
        if not isinstance(regions, list):
            return
        for region in regions:
            if not isinstance(region, dict):
                continue
            for item in region.get("itemInstances", []):
                if not isinstance(item, dict):
                    continue
                comp = item.get("componentInstance", {})
                if isinstance(comp, dict):
                    name = comp.get("componentName", "")
                    # Only warn for force: / flexipage: prefixed names we know are wrong.
                    if name == "force:recordDetail":
                        self._deduct(
                            "schema", 3,
                            "Component 'force:recordDetail' should be 'force:detailPanel'",
                            "warning",
                        )

    def _check_flexipage_visibility_rules(self):
        """Flag unsupported visibility-rule operators."""
        regions = self.payload.get("flexiPageRegions", [])
        if not isinstance(regions, list):
            return
        for region in regions:
            if not isinstance(region, dict):
                continue
            for item in region.get("itemInstances", []):
                if not isinstance(item, dict):
                    continue
                comp = item.get("componentInstance", {})
                if not isinstance(comp, dict):
                    continue
                vis = comp.get("visibilityRule")
                if not isinstance(vis, dict):
                    continue
                for criterion in vis.get("criteria", []):
                    if not isinstance(criterion, dict):
                        continue
                    op = criterion.get("operator", "")
                    if op and op not in FLEXIPAGE_VISIBILITY_OPERATORS:
                        self._deduct(
                            "deployability", 6,
                            f"Visibility rule operator '{op}' is unsupported; only EQUAL is confirmed to work",
                            "critical",
                        )

    def _check_layout_schema(self):
        """Validate Layout-specific structure."""
        sections = self.payload.get("layoutSections", [])
        if isinstance(sections, list):
            for i, section in enumerate(sections):
                if not isinstance(section, dict):
                    continue
                style = section.get("style", "")
                if style and style not in LAYOUT_SECTION_STYLES:
                    self._deduct("schema", 4, f"Section {i} has invalid style '{style}'", "critical")
                # Validate item behaviors.
                for col in section.get("layoutColumns", []):
                    if not isinstance(col, dict):
                        continue
                    for item in col.get("layoutItems", []):
                        if not isinstance(item, dict):
                            continue
                        behavior = item.get("behavior", "")
                        if behavior and behavior not in LAYOUT_ITEM_BEHAVIORS:
                            self._deduct(
                                "schema", 3,
                                f"Layout item behavior '{behavior}' is invalid; use Edit, Required, or Readonly",
                                "warning",
                            )

    def _deduct(self, category: str, points: int, message: str, severity: str):
        cat = self.categories[category]
        cat["score"] = max(0, cat["score"] - points)
        cat["issues"].append(message)
        self.issues.append({"category": category, "severity": severity, "message": message, "points": points})

    def _check_identity_key_present(self) -> bool:
        """Check that the type-appropriate identity key is present."""
        if self.metadata_type == "FlexiPage":
            return "masterLabel" in self.payload
        if self.metadata_type == "Layout":
            return True  # Layouts are identified by their full name in the API call, not in the payload.
        return "fullName" in self.payload

    def _result(self) -> dict[str, Any]:
        total = sum(info["score"] for info in self.categories.values())
        if any(issue["severity"] == "critical" for issue in self.issues):
            status = "critical"
        elif total >= MAX_SCORE * 0.8:
            status = "pass"
        elif total >= MAX_SCORE * 0.6:
            status = "needs_attention"
        else:
            status = "fail"
        return {
            "metadata_type": self.metadata_type,
            "overall_score": total,
            "max_score": MAX_SCORE,
            "status": status,
            "categories": self.categories,
            "issues": self.issues,
            "required_keys_present": self._check_identity_key_present(),
        }


def analyze_formula_safety(formula: str) -> list[str]:
    """Detect parser edge-case patterns likely to break regex/line scanners."""
    if not formula:
        return []

    findings: list[str] = []

    if re.search(r"for\s*\([^)]*\)\s*\{[^}]*\}", formula, re.IGNORECASE):
        findings.append("single-line braced loop syntax found")
    if re.search(r"for\s*\([^)]*\)\s*[^\s{]", formula, re.IGNORECASE):
        findings.append("braceless loop syntax found")
    if re.search(r"do\s*\{[\s\S]*?\}\s*while\s*\([^)]*\)", formula, re.IGNORECASE):
        findings.append("do/while loop style found")
    if "==" in formula:
        findings.append("double equals operator found")

    return findings
