#!/usr/bin/env python3
"""
Flow XML Schema Validator
=========================

Converts Salesforce Flow XML to a JSON representation and validates it
against the JSON Schema in references/flow-metadata-schema.json.

This catches syntactic issues that the anti-pattern validator (validate_flow.py)
does not cover:
  - Unknown/misspelled element names
  - Missing required fields (e.g. label, name)
  - Wrong data types
  - Invalid enum values (processType, triggerType, etc.)

Usage:
    from validate_flow_schema import FlowSchemaValidator
    result = FlowSchemaValidator("path/to/flow.flow-meta.xml").validate()
    # result = {"valid": True/False, "errors": [...]}

CLI:
    python validate_flow_schema.py path/to/flow.flow-meta.xml
"""

import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Any

import jsonschema

# ═══════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REFERENCES_DIR = os.path.join(os.path.dirname(_SCRIPT_DIR), "references")
_SCHEMA_PATH = os.path.join(_REFERENCES_DIR, "flow-metadata-schema.json")

_SF_NS = "http://soap.sforce.com/2006/04/metadata"
_NS_PREFIX = f"{{{_SF_NS}}}"


# ═══════════════════════════════════════════════════════════════════════
# Schema property resolution (with allOf inheritance)
# ═══════════════════════════════════════════════════════════════════════


def _resolve_all_properties(schema: dict, def_name: str) -> dict:
    """Collect all properties for a $def, including those inherited via allOf."""
    defs = schema.get("$defs", {})
    definition = defs.get(def_name, {})
    props = dict(definition.get("properties", {}))

    # Walk allOf refs to collect inherited properties
    for entry in definition.get("allOf", []):
        ref = entry.get("$ref", "")
        if ref:
            parent_name = ref.split("/")[-1]
            parent_props = _resolve_all_properties(schema, parent_name)
            # Parent props are inherited — don't overwrite child overrides
            for k, v in parent_props.items():
                props.setdefault(k, v)
        # Inline properties in allOf entries
        for k, v in entry.get("properties", {}).items():
            props.setdefault(k, v)

    return props


def _get_field_info(schema: dict, parent_def: str, field_name: str) -> dict:
    """Get the schema property definition for a field, resolving allOf."""
    props = _resolve_all_properties(schema, parent_def)
    return props.get(field_name, {})


def _get_schema_type(schema: dict, parent_def: str, field_name: str) -> str | None:
    """Look up the expected type for a field from the JSON schema."""
    prop = _get_field_info(schema, parent_def, field_name)
    if not prop:
        return None

    ptype = prop.get("type")
    if ptype == "array":
        return "array"
    if ptype in ("number", "integer"):
        return "number"
    if ptype == "boolean":
        return "boolean"
    if "$ref" in prop:
        return "object"
    return ptype


def _get_array_item_ref(schema: dict, parent_def: str, field_name: str) -> str | None:
    """Get the $ref target for array items."""
    prop = _get_field_info(schema, parent_def, field_name)
    if prop.get("type") == "array":
        items = prop.get("items", {})
        ref = items.get("$ref", "")
        if ref:
            return ref.split("/")[-1]
    return None


def _get_object_ref(schema: dict, parent_def: str, field_name: str) -> str | None:
    """Get the $ref target for an object field."""
    prop = _get_field_info(schema, parent_def, field_name)
    ref = prop.get("$ref", "")
    if ref:
        return ref.split("/")[-1]
    return None


# ═══════════════════════════════════════════════════════════════════════
# XML → JSON conversion
# ═══════════════════════════════════════════════════════════════════════


def _load_schema() -> dict:
    """Load the JSON schema."""
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _strip_ns(tag: str) -> str:
    """Remove the Salesforce namespace prefix from an XML tag."""
    if tag.startswith(_NS_PREFIX):
        return tag[len(_NS_PREFIX):]
    return tag


def _coerce_value(value: str, schema_type: str | None) -> Any:
    """Coerce a string value to the appropriate Python type."""
    if schema_type == "number":
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value
    if schema_type == "boolean":
        return value.lower() == "true"
    return value


def xml_to_json(element: ET.Element, schema: dict, schema_def: str = "Flow") -> dict:
    """Convert an XML element to a JSON dict using schema type info.

    Uses the JSON schema (with allOf inheritance resolution) to determine:
      - Which fields are arrays (collect multiple same-named children)
      - Which fields are numbers/booleans (coerce from string)
      - Which fields are nested objects (recurse with correct schema def)
    """
    result: dict[str, Any] = {}

    # Group children by tag name
    children_by_tag: dict[str, list[ET.Element]] = {}
    for child in element:
        tag = _strip_ns(child.tag)
        children_by_tag.setdefault(tag, []).append(child)

    for tag, children in children_by_tag.items():
        schema_type = _get_schema_type(schema, schema_def, tag)

        if schema_type == "array":
            item_ref = _get_array_item_ref(schema, schema_def, tag)
            items = []
            for child in children:
                if len(child) > 0 and item_ref:
                    items.append(xml_to_json(child, schema, item_ref))
                elif child.text and child.text.strip():
                    items.append(_coerce_value(child.text.strip(), None))
                else:
                    if item_ref:
                        items.append(xml_to_json(child, schema, item_ref))
                    else:
                        items.append(child.text.strip() if child.text else "")
            result[tag] = items

        elif schema_type == "object" or (schema_type is None and len(children) == 1 and len(children[0]) > 0):
            child = children[0]
            obj_ref = _get_object_ref(schema, schema_def, tag)
            if obj_ref:
                result[tag] = xml_to_json(child, schema, obj_ref)
            elif len(child) > 0:
                result[tag] = xml_to_json(child, schema, tag)
            else:
                result[tag] = child.text.strip() if child.text else ""

        elif len(children) > 1:
            item_ref = (_get_array_item_ref(schema, schema_def, tag)
                        or _get_object_ref(schema, schema_def, tag))
            items = []
            for child in children:
                if len(child) > 0:
                    items.append(xml_to_json(child, schema, item_ref or tag))
                else:
                    items.append(_coerce_value(
                        child.text.strip() if child.text else "", schema_type))
            result[tag] = items

        else:
            child = children[0]
            if len(child) > 0:
                obj_ref = _get_object_ref(schema, schema_def, tag)
                result[tag] = xml_to_json(child, schema, obj_ref or tag)
            else:
                text = child.text.strip() if child.text else ""
                result[tag] = _coerce_value(text, schema_type)

    return result


# ═══════════════════════════════════════════════════════════════════════
# Validator
# ═══════════════════════════════════════════════════════════════════════


class FlowSchemaValidator:
    """Validate Flow XML against the JSON schema.

    Usage:
        result = FlowSchemaValidator("path.flow-meta.xml").validate()
        assert result["valid"]
    """

    def __init__(self, flow_path: str):
        self.flow_path = flow_path
        self._schema = _load_schema()

    def validate(self) -> dict[str, Any]:
        """Parse the XML, convert to JSON, validate against schema.

        Returns:
            {
                "valid": bool,
                "errors": [{"path": str, "message": str}, ...],
                "flow_json": dict  (the converted JSON for debugging),
            }
        """
        errors: list[dict[str, str]] = []

        # Step 1: Parse XML
        try:
            tree = ET.parse(self.flow_path)
            root = tree.getroot()
        except ET.ParseError as e:
            return {
                "valid": False,
                "errors": [{"path": "", "message": f"XML parse error: {e}"}],
                "flow_json": {},
            }

        # Verify root element
        root_tag = _strip_ns(root.tag)
        if root_tag != "Flow":
            errors.append({
                "path": "",
                "message": f"Root element is '{root_tag}', expected 'Flow'",
            })
            return {"valid": False, "errors": errors, "flow_json": {}}

        # Step 2: Convert to JSON
        flow_json = xml_to_json(root, self._schema, "Flow")

        # Step 3: Validate against schema
        flow_schema = self._schema.get("$defs", {}).get("Flow", {})

        # Use RefResolver (deprecated but functional in jsonschema 4.x)
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            resolver = jsonschema.RefResolver.from_schema(self._schema)
            validator = jsonschema.Draft202012Validator(
                flow_schema,
                resolver=resolver,
            )

        for error in validator.iter_errors(flow_json):
            path = ".".join(str(p) for p in error.absolute_path) or "(root)"
            errors.append({
                "path": path,
                "message": error.message,
            })

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "flow_json": flow_json,
        }


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_flow_schema.py <flow.flow-meta.xml>")
        sys.exit(1)

    path = sys.argv[1]
    result = FlowSchemaValidator(path).validate()

    if result["valid"]:
        print(f"VALID: {path}")
    else:
        print(f"INVALID: {path} ({len(result['errors'])} errors)")
        for err in result["errors"]:
            print(f"  [{err['path']}] {err['message']}")

    sys.exit(0 if result["valid"] else 1)
