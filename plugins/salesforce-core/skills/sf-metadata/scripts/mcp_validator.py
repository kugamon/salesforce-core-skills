#!/usr/bin/env python3
"""MCP validator adapter for Salesforce metadata operations."""

from __future__ import annotations

import importlib.util
import os
from typing import Any

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_VALIDATE_SCRIPT = os.path.join(_SCRIPT_DIR, "validate_metadata_operation.py")

_spec = importlib.util.spec_from_file_location("validate_metadata_operation", _VALIDATE_SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
MetadataOperationValidator = _mod.MetadataOperationValidator
SUPPORTED_METADATA_TYPES = _mod.SUPPORTED_METADATA_TYPES

SUPPORTED_TOOLS = ("metadata_create", "metadata_update", "tooling_api_dml", "metadata_read")


def _extract_metadata(tool: str, params: dict[str, Any]) -> tuple[str, dict[str, Any], str, int]:
    """Return (metadata_type, payload, full_name, batch_size)."""
    metadata_type = ""
    payload: dict[str, Any] = {}
    full_name = ""
    batch_size = 0

    if tool in ("metadata_create", "metadata_update"):
        metadata_type = params.get("type", "")
        metadata = params.get("metadata", [])
        if isinstance(metadata, list):
            batch_size = len(metadata)
            if metadata:
                first = metadata[0]
                if isinstance(first, dict):
                    payload = first
                    full_name = str(first.get("fullName", first.get("masterLabel", "")))

    elif tool == "metadata_read":
        metadata_type = params.get("type", "")
        full_names = params.get("fullNames", [])
        batch_size = len(full_names) if isinstance(full_names, list) else 0
        if full_names:
            full_name = str(full_names[0])
        # metadata_read is read-only; provide a minimal payload for type-level checks.
        payload = {"fullName": full_name} if full_name else {}

    elif tool == "tooling_api_dml":
        sobject = params.get("sObject", "")
        record = params.get("record", {})
        metadata_type = sobject
        batch_size = 1
        if isinstance(record, dict):
            payload = record.get("Metadata", {}) if isinstance(record.get("Metadata"), dict) else {}
            full_name = str(record.get("FullName", ""))
            if full_name and "fullName" not in payload:
                payload = {**payload, "fullName": full_name}

    return metadata_type, payload, full_name, batch_size


def validate_metadata_deployment(input_data: dict[str, Any]) -> dict[str, Any]:
    tool = input_data.get("tool", "")
    params = input_data.get("params", {})

    base = {
        "tier": "metadata_deployment",
        "tool": tool,
        "metadata_type": "",
        "status": "error",
        "validator": "MetadataOperationValidator",
    }

    if tool not in SUPPORTED_TOOLS:
        return {**base, "message": f"Unsupported tool '{tool}'"}

    metadata_type, payload, full_name, batch_size = _extract_metadata(tool, params)
    base.update({"metadata_type": metadata_type, "full_name": full_name})

    if not metadata_type:
        return {**base, "message": "Could not determine metadata type from MCP payload"}

    if metadata_type not in SUPPORTED_METADATA_TYPES:
        return {
            **base,
            "status": "skipped",
            "message": f"Metadata type '{metadata_type}' is not handled by this validator",
        }

    if not payload:
        return {**base, "message": "Missing or empty metadata payload"}

    # metadata_read is read-only — skip full payload validation and return
    # a lightweight acknowledgement that the type is supported.
    if tool == "metadata_read":
        return {
            **base,
            "status": "scored",
            "quality_status": "pass",
            "overall_score": 0,
            "max_score": 0,
            "categories": {},
            "issues": [],
            "message": f"Read operation for '{metadata_type}' — no payload to validate",
        }

    result = MetadataOperationValidator(metadata_type, payload).validate()
    quality_status = result.pop("status", "unknown")
    response = {**base, **result, "status": "scored", "quality_status": quality_status}
    if batch_size > 1:
        response["batch_warning"] = (
            f"Only the first of {batch_size} metadata items was validated. "
            "Submit items individually for complete coverage."
        )
    return response


class MetadataMCPValidator:
    """Entry point wrapper used by hooks and tests."""

    def validate(self, input_data: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata_deployment(input_data)
