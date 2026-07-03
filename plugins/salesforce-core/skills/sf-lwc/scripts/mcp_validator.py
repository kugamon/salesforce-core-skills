#!/usr/bin/env python3
"""MCP validation adapter for LWC metadata deployments.

Validates LightningComponentBundle payloads sent through metadata MCP tools and
returns a stable, machine-readable result for orchestration logic.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

_SCRIPT_DIR = str(Path(__file__).resolve().parent)

SUPPORTED_TOOLS = ("metadata_create", "metadata_update", "tooling_api_dml")
TARGET_METADATA_TYPE = "LightningComponentBundle"


def _extract_payload(tool: str, params: dict[str, Any]) -> tuple[str, str, str]:
    """Extract (metadata_type, content, full_name) from MCP params."""
    metadata_type = ""
    content = ""
    full_name = ""

    if tool in ("metadata_create", "metadata_update"):
        metadata_type = params.get("type", "")
        metadata_list = params.get("metadata", [])
        if isinstance(metadata_list, list) and metadata_list:
            first = metadata_list[0]
            if isinstance(first, dict):
                full_name = first.get("fullName", "")
                # Most common representations for tests and integrations.
                content = first.get("content", "") or first.get("body", "") or first.get("html", "")

                if not content:
                    resources_raw = first.get("lwcResources", [])
                    # The MCP tool sends {"lwcResource": [...]} (dict), not a flat list.
                    # Handle both formats for forward compatibility.
                    if isinstance(resources_raw, dict):
                        resources = resources_raw.get("lwcResource", [])
                    elif isinstance(resources_raw, list):
                        resources = resources_raw
                    else:
                        resources = []
                    if isinstance(resources, list):
                        html_sources = [
                            r.get("source", "")
                            for r in resources
                            if isinstance(r, dict) and str(r.get("filePath", "")).endswith(".html")
                        ]
                        content = "\n".join([s for s in html_sources if s])

    elif tool == "tooling_api_dml":
        sobject = params.get("sObject", "")
        metadata_type = TARGET_METADATA_TYPE if sobject == TARGET_METADATA_TYPE else sobject
        record = params.get("record", {})
        if isinstance(record, dict):
            full_name = record.get("FullName", "") or record.get("DeveloperName", "")
            raw = record.get("Body", "") or record.get("Metadata", "")
            content = raw if isinstance(raw, str) else ""

    return metadata_type, content, full_name


class LWCMCPValidator:
    """Validate MCP deployment payloads for LightningComponentBundle."""

    def validate(self, input_data: dict[str, Any]) -> dict[str, Any]:
        tool = input_data.get("tool", "")
        params = input_data.get("params", {}) or {}

        base = {
            "tier": "metadata",
            "tool": tool,
            "metadata_type": "",
            "status": "error",
            "validator": "sf-lwc.mcp_validator",
        }

        if tool not in SUPPORTED_TOOLS:
            return {
                **base,
                "status": "error",
                "message": f"Unsupported tool '{tool}'",
            }

        metadata_type, content, full_name = _extract_payload(tool, params)
        base["metadata_type"] = metadata_type
        if full_name:
            base["full_name"] = full_name

        if metadata_type != TARGET_METADATA_TYPE:
            return {
                **base,
                "status": "skipped",
                "message": f"Metadata type '{metadata_type}' is not targeted by this validator",
            }

        if not str(content).strip():
            return {
                **base,
                "status": "error",
                "message": "Missing or empty LWC payload content",
            }

        try:
            if _SCRIPT_DIR not in sys.path:
                sys.path.insert(0, _SCRIPT_DIR)
            from template_validator import LWCTemplateValidator
            from validate_slds import SLDSValidator

            with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
                f.write(content)
                temp_path = f.name

            try:
                slds = SLDSValidator(temp_path).validate()
                template = LWCTemplateValidator(temp_path).validate()
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

            max_score = slds.get("max_score", 0) or 1
            base_score = slds.get("score", 0)
            critical = [i for i in template.get("issues", []) if i.get("severity") == "CRITICAL"]
            warnings = [i for i in template.get("issues", []) if i.get("severity") == "WARNING"]

            adjusted_score = max(0, base_score - (len(critical) * 3))

            return {
                **base,
                "status": "scored",
                "score": adjusted_score,
                "max_score": max_score,
                "critical_count": len(critical),
                "warning_count": len(warnings),
                "issues": template.get("issues", []),
            }
        except Exception as exc:  # pragma: no cover - safety fallback
            return {
                **base,
                "status": "error",
                "message": f"Validation failed: {exc}",
            }


__all__ = ["LWCMCPValidator"]
