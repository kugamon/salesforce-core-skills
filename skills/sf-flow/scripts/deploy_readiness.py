#!/usr/bin/env python3
"""Flow deployment readiness checker.

Validates Flow XML files against known structural requirements that cause
InvalidDraft status on Salesforce deployment.  These checks were derived from
actual MCP metadata_create deployments to a Salesforce sandbox.

Usage as a library:
    from deploy_readiness import check_deploy_readiness
    result = check_deploy_readiness("path/to/flow.flow-meta.xml")
    # result = {"ready": True/False, "issues": [...]}

    # With org field verification:
    result = check_deploy_readiness("path/to/flow.flow-meta.xml",
                                     org_fields=["Field1__c", "Field2__c"])

Usage as CLI:
    python deploy_readiness.py path/to/flow.flow-meta.xml
    python deploy_readiness.py --org-fields Field1__c,Field2__c path/to/flow.xml
"""

import json
import re
import sys
import xml.etree.ElementTree as ET

_SF_NS = "http://soap.sforce.com/2006/04/metadata"
_NS = {"sf": _SF_NS}


# -- helpers ------------------------------------------------------------------


def _parse_flow(path: str) -> ET.Element:
    return ET.parse(path).getroot()


def _find(root: ET.Element, xpath: str) -> list[ET.Element]:
    return root.findall(xpath, _NS)


def _get_text(root: ET.Element, xpath: str) -> str | None:
    el = root.find(xpath, _NS)
    return el.text.strip() if el is not None and el.text else None


def _has_schedule(root: ET.Element) -> bool:
    return root.find(".//sf:start/sf:schedule", _NS) is not None


def _has_trigger_type(root: ET.Element, expected: str | None = None) -> bool:
    tt = root.find(".//sf:start/sf:triggerType", _NS)
    if tt is None:
        return False
    if expected:
        return tt.text and tt.text.strip() == expected
    return True


def _has_bulk_support(root: ET.Element) -> bool:
    return root.find(".//sf:bulkSupport", _NS) is not None


def _get_api_version(root: ET.Element) -> float:
    v = _get_text(root, "sf:apiVersion")
    return float(v) if v else 0.0


_FIELD_REF_TAGS = frozenset({
    "assignToReference", "field", "elementReference",
    "inputReference", "outputReference", "assignNullValuesIfNoRecordsFound",
})

# Matches $Record.Field__c, {!var.Field__c}, or currentItem.Field__c patterns.
_FIELD_REF_RE = re.compile(r"(?:\$Record|currentItem|\{![^}.]+)\.\w+__c\b")


def _get_custom_field_refs(root: ET.Element) -> list[str]:
    """Find references to custom fields (__c) in assignment/filter elements.

    Only scans elements whose local tag name is a known field-reference tag,
    or whose text matches a ``$Record.Field__c`` / ``{!var.Field__c}`` pattern.
    This avoids false positives from ``<object>``, ``<description>``, and other
    free-text elements that may mention custom API names.
    """
    refs = []
    for el in root.iter():
        text = el.text
        if not text or "__c" not in text:
            continue
        # Strip namespace prefix to get local tag name.
        local_tag = el.tag.rsplit("}", 1)[-1] if "}" in el.tag else el.tag
        if local_tag in _FIELD_REF_TAGS or _FIELD_REF_RE.search(text):
            refs.append(text.strip())
    return refs


def _get_trigger_object(root: ET.Element) -> str | None:
    """Extract the trigger object from a record-triggered flow."""
    start = root.find("sf:start", _NS)
    if start is not None:
        obj = start.find("sf:object", _NS)
        if obj is not None and obj.text:
            return obj.text.strip()
    return None


def _extract_field_names_from_refs(refs: list[str]) -> list[str]:
    """Extract bare field API names from $Record.Field__c style references.

    Only considers references that contain a dot (e.g. ``$Record.Field__c``,
    ``currentItem.Status__c``) to avoid misidentifying standalone object API
    names like ``Custom_Object__c`` as field names.
    """
    fields = []
    for ref in refs:
        if "." not in ref:
            continue
        field = ref.rsplit(".", 1)[-1]
        if field.endswith("__c") and field not in fields:
            fields.append(field)
    return fields


# -- main check ---------------------------------------------------------------


def check_deploy_readiness(path: str, org_fields: list[str] | None = None) -> dict:
    """Run deployment-readiness checks against a flow XML file.

    Args:
        path: Path to a .flow-meta.xml file.
        org_fields: Optional list of field API names that exist on the trigger
            object in the target org.  When provided, custom field references
            are checked against this list — missing fields are promoted from
            WARN to ERROR.

    Returns dict with:
      - ready: bool (True = will deploy as Draft, not InvalidDraft)
      - issues: list of issue dicts with severity and message
    """
    root = _parse_flow(path)
    issues = []

    # Check 1: Scheduled flows must have triggerType=Scheduled
    if _has_schedule(root) and not _has_trigger_type(root, "Scheduled"):
        issues.append({
            "severity": "ERROR",
            "check": "scheduled_trigger_type",
            "message": (
                "Flow has <schedule> in <start> but missing "
                "<triggerType>Scheduled</triggerType>. "
                "This causes InvalidDraft status — flow cannot be activated."
            ),
        })

    # Check 2: No bulkSupport (removed in API 60.0+)
    api_version = _get_api_version(root)
    if _has_bulk_support(root):
        issues.append({
            "severity": "ERROR" if api_version >= 60.0 else "WARN",
            "check": "deprecated_bulk_support",
            "message": (
                "<bulkSupport> was removed in API 60.0+. "
                "Remove it to avoid deployment issues."
            ),
        })

    # Check 3: Custom field references — warn or error depending on org_fields
    custom_refs = _get_custom_field_refs(root)
    if custom_refs:
        field_names = _extract_field_names_from_refs(custom_refs)
        if org_fields is not None:
            org_fields_set = set(org_fields)
            missing = [f for f in field_names if f not in org_fields_set]
            present = [f for f in field_names if f in org_fields_set]
            if missing:
                issues.append({
                    "severity": "ERROR",
                    "check": "missing_custom_fields",
                    "message": (
                        f"Flow references custom fields that do NOT exist "
                        f"on the target object: {missing}. "
                        "Create these fields before deploying the flow."
                    ),
                })
            if present:
                issues.append({
                    "severity": "INFO",
                    "check": "custom_field_references",
                    "message": (
                        f"Flow references custom fields (verified present): "
                        f"{present}."
                    ),
                })
        else:
            issues.append({
                "severity": "WARN",
                "check": "custom_field_references",
                "message": (
                    f"Flow references custom fields: {custom_refs}. "
                    "These must exist in the target org or activation will fail."
                ),
            })

    # Check 4: Record-triggered flows must have triggerType
    start = root.find("sf:start", _NS)
    if start is not None:
        has_object = start.find("sf:object", _NS) is not None
        has_record_trigger = start.find("sf:recordTriggerType", _NS) is not None
        if has_object and has_record_trigger and not _has_trigger_type(root):
            issues.append({
                "severity": "ERROR",
                "check": "record_trigger_type",
                "message": (
                    "Record-triggered flow has <object> and <recordTriggerType> "
                    "but missing <triggerType>. This causes InvalidDraft status."
                ),
            })

    errors = [i for i in issues if i["severity"] == "ERROR"]
    return {"ready": len(errors) == 0, "issues": issues}


# -- CLI ----------------------------------------------------------------------


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check flow deployment readiness")
    parser.add_argument("flow_file", help="Path to .flow-meta.xml file")
    parser.add_argument(
        "--org-fields",
        help="Comma-separated list of field API names present on the trigger object",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    org_fields = args.org_fields.split(",") if args.org_fields else None
    result = check_deploy_readiness(args.flow_file, org_fields=org_fields)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "READY" if result["ready"] else "NOT READY"
        print(f"Deploy readiness: {status}")
        for issue in result["issues"]:
            print(f"  [{issue['severity']}] {issue['check']}: {issue['message']}")

    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
