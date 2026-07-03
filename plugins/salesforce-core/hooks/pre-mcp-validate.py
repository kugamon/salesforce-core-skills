#!/usr/bin/env python3
"""
Plugin-level PreToolUse hook dispatcher for salesforce-core-skills.

Reads the hook input from stdin, determines the metadata type, runs
JSON Schema validation on the metadata payload, then delegates to the
appropriate sub-skill validator script for deeper analysis.

Currently registered delegates:
  - sf-apex: ApexClass, ApexTrigger
  - sf-flow: Flow, FlowDefinition
  - sf-data: soql_query, sobject_dml (routed by tool name)
  - sf-lwc: LightningComponentBundle
  - sf-metadata: CustomObject, CustomField, ValidationRule, RecordType, PermissionSet
"""

import json
import os
import subprocess
import sys
from typing import Any

_PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(os.path.dirname(_PLUGIN_ROOT))

# Map metadata types to their validator script (relative to _PLUGIN_ROOT).
# Add new entries here as sub-skills gain their own pre-deploy validators.
_DELEGATES: dict[str, str] = {
    "ApexClass":      "skills/sf-apex/scripts/pre-mcp-validate.py",
    "ApexTrigger":    "skills/sf-apex/scripts/pre-mcp-validate.py",
    "Flow":                       "skills/sf-flow/scripts/pre-mcp-validate.py",
    "FlowDefinition":             "skills/sf-flow/scripts/pre-mcp-validate.py",
    "LightningComponentBundle":   "skills/sf-lwc/scripts/pre-mcp-validate.py",
    "CustomObject":               "skills/sf-metadata/scripts/pre-mcp-validate.py",
    "CustomField":                "skills/sf-metadata/scripts/pre-mcp-validate.py",
    "ValidationRule":             "skills/sf-metadata/scripts/pre-mcp-validate.py",
    "RecordType":                 "skills/sf-metadata/scripts/pre-mcp-validate.py",
    "PermissionSet":              "skills/sf-metadata/scripts/pre-mcp-validate.py",
}

# Map base tool names to their validator script (relative to _PLUGIN_ROOT).
# Used for tools like soql_query / sobject_dml that aren't metadata types.
_TOOL_DELEGATES: dict[str, str] = {
    "soql_query":  "skills/sf-data/scripts/pre-mcp-validate.py",
    "sobject_dml": "skills/sf-data/scripts/pre-mcp-validate.py",
}

# Map metadata types to their JSON Schema file (relative to _REPO_ROOT).
_SCHEMAS: dict[str, str] = {
    "CustomField":       "skills/sf-metadata/references/customfield-metadata-schema.json",
    "CustomObject":      "skills/sf-metadata/references/customobject-metadata-schema.json",
    "FlexiPage":         "skills/sf-metadata/references/flexipage-metadata-schema.json",
    "Layout":            "skills/sf-metadata/references/layout-metadata-schema.json",
    "QuickAction":       "skills/sf-metadata/references/quickaction-metadata-schema.json",
    "RecordType":        "skills/sf-metadata/references/recordtype-metadata-schema.json",
    "ValidationRule":    "skills/sf-metadata/references/validationrule-metadata-schema.json",
    "PermissionSet":     "skills/sf-permissions/references/permissionset-metadata-schema.json",
    "PermissionSetGroup": "skills/sf-permissions/references/permissionsetgroup-metadata-schema.json",
    "Profile":           "skills/sf-permissions/references/profile-metadata-schema.json",
    "SharingRules":      "skills/sf-permissions/references/sharingrules-metadata-schema.json",
}
# Note: Flow and FlowDefinition are NOT in _SCHEMAS because they have
# delegate validators that provide richer feedback (110-point rubric).

# Cache loaded schemas to avoid re-reading per item.
_schema_cache: dict[str, dict] = {}


def _allow(context: str = "") -> dict:
    out: dict = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
    if context:
        out["hookSpecificOutput"]["additionalContext"] = context
    return out


def _metadata_type(tool_name: str, tool_input: dict) -> str:
    """Extract the metadata type from hook input fields."""
    base_tool = tool_name.split("__")[-1] if tool_name.startswith("mcp__") else tool_name

    if base_tool in ("metadata_create", "metadata_update"):
        return tool_input.get("type", "")
    if base_tool == "tooling_api_dml":
        return tool_input.get("sObject", "")
    return ""


def _load_schema(metadata_type: str) -> dict | None:
    """Load and cache the JSON Schema for a metadata type. Returns None if unavailable."""
    if metadata_type in _schema_cache:
        return _schema_cache[metadata_type]

    rel_path = _SCHEMAS.get(metadata_type)
    if not rel_path:
        return None

    schema_path = os.path.join(_REPO_ROOT, rel_path)
    if not os.path.isfile(schema_path):
        return None

    try:
        with open(schema_path) as f:
            schema = json.load(f)
        _schema_cache[metadata_type] = schema
        return schema
    except Exception:
        return None


def _extract_metadata_items(tool_input: dict) -> list[dict]:
    """Extract the metadata item dicts to validate from the tool input."""
    # metadata_create / metadata_update: params.metadata is a list of dicts
    metadata_list = tool_input.get("metadata")
    if isinstance(metadata_list, list) and metadata_list:
        return [m for m in metadata_list if isinstance(m, dict)]

    # tooling_api_dml: params.record is a single dict
    record = tool_input.get("record")
    if isinstance(record, dict):
        return [record]

    return []


def _validate_schema(metadata_type: str, tool_input: dict) -> str | None:
    """Run JSON Schema validation on metadata items.

    Returns an error message string if validation fails, or None if it passes
    (or if no schema is available for the type).
    """
    schema = _load_schema(metadata_type)
    if schema is None:
        return None

    try:
        import jsonschema
    except ImportError:
        jsonschema = None

    items = _extract_metadata_items(tool_input)
    if not items:
        return None

    errors: list[str] = []
    for i, item in enumerate(items):
        if jsonschema is not None:
            try:
                jsonschema.validate(instance=item, schema=schema)
            except jsonschema.ValidationError as exc:
                path = " → ".join(str(p) for p in exc.absolute_path) if exc.absolute_path else "(root)"
                name = item.get("fullName", item.get("FullName", f"item[{i}]"))
                errors.append(f"'{name}' at {path}: {exc.message}")
        else:
            errors.extend(_basic_schema_errors(item, schema, i))

    if not errors:
        return None

    header = f"JSON Schema validation failed for {metadata_type}:\n"
    detail = "\n".join(f"• {e}" for e in errors[:5])
    if len(errors) > 5:
        detail += f"\n• ...and {len(errors) - 5} more errors"
    return header + detail


def _basic_schema_errors(item: dict, schema: dict, index: int) -> list[str]:
    """Lightweight fallback validation for required/type fields.

    Used when jsonschema is unavailable in local environments.
    """
    errs: list[str] = []
    name = item.get("fullName", item.get("FullName", f"item[{index}]"))

    schema = _resolve_local_ref(schema, schema)

    required = schema.get("required", [])
    for field in required:
        if field not in item:
            errs.append(f"'{name}' at {field}: is a required property")

    type_map = {
        "boolean": bool,
        "string": str,
        "number": (int, float),
        "integer": int,
        "object": dict,
        "array": list,
    }
    root_schema = schema
    properties = schema.get("properties", {})
    for field, rules in properties.items():
        if field not in item or not isinstance(rules, dict):
            continue
        rules = _resolve_local_ref(rules, root_schema)
        expected_type = rules.get("type")
        if not isinstance(expected_type, str):
            continue
        expected_py = type_map.get(expected_type)
        if expected_py is None:
            continue
        value = item[field]
        if isinstance(value, bool) and expected_type in ("integer", "number"):
            errs.append(
                f"'{name}' at {field}: {value!r} is not of type '{expected_type}'"
            )
        elif not isinstance(value, expected_py):
            errs.append(
                f"'{name}' at {field}: {value!r} is not of type '{expected_type}'"
            )

    return errs


def _resolve_local_ref(schema: dict, root_schema: dict) -> dict:
    """Resolve simple local ``$ref`` pointers like ``#/$defs/Type``."""
    ref = schema.get("$ref") if isinstance(schema, dict) else None
    if not ref or not ref.startswith("#/"):
        return schema

    node: Any = root_schema
    for part in ref[2:].split("/"):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return schema
    return node if isinstance(node, dict) else schema


def main() -> int:
    try:
        raw = sys.stdin.buffer.read()
        hook_input = json.loads(raw)
    except Exception:
        print(json.dumps(_allow()))
        return 0

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # --- Delegate by base tool name (data operations) ---
    parts = tool_name.split("__", 2)
    base_tool = parts[2] if tool_name.startswith("mcp__") and len(parts) > 2 else tool_name

    tool_delegate = _TOOL_DELEGATES.get(base_tool)
    if tool_delegate:
        script_path = os.path.join(_PLUGIN_ROOT, tool_delegate)
        result = subprocess.run(
            [sys.executable, script_path],
            input=raw,
            capture_output=True,
        )
        output = result.stdout.strip()
        if output:
            print(output.decode("utf-8", errors="replace"))
        else:
            print(json.dumps(_allow()))
        return 0

    # --- Delegate by metadata type (Apex, Flow, etc.) ---
    metadata_type = _metadata_type(tool_name, tool_input)

    if not metadata_type:
        print(json.dumps(_allow()))
        return 0

    # --- Delegate to sub-skill custom validator (takes priority) ---
    delegate_script = _DELEGATES.get(metadata_type)
    if delegate_script:
        script_path = os.path.join(_PLUGIN_ROOT, delegate_script)
        result = subprocess.run(
            [sys.executable, script_path],
            input=raw,
            capture_output=True,
        )

        output = result.stdout.strip()
        if output:
            print(output.decode("utf-8", errors="replace"))
        else:
            print(json.dumps(_allow()))
        return 0

    # --- JSON Schema validation (for types without a delegate) ---
    # Flag schema issues but never block the operation.
    schema_error = _validate_schema(metadata_type, tool_input)
    if schema_error:
        print(json.dumps(_allow(f"🚨 {schema_error}")))
        return 0

    print(json.dumps(_allow()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
