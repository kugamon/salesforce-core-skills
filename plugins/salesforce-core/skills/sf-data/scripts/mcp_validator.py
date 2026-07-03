#!/usr/bin/env python3
"""
MCP Data Operation Validator
==============================

Validates Salesforce MCP data tool parameters with lightweight pass/fail checks.

Covers soql_query and sobject_dml — the interactive data operations.
No scoring; just structural error/warning checks that catch things that would
fail or leak data. Running an inefficient query interactively is fine; governor
limits protect you.

For code deployment validation (Apex, Flows), use the validators in
sf-apex or sf-flow respectively.

Input format:
{
  "tool": "soql_query" | "sobject_dml",
  "params": { ... MCP tool parameters ... },
  "context": { "purpose": "optional description" }
}
"""

import re
from typing import Any


# ═══════════════════════════════════════════════════════════════════════
# Data Parameter Checks — lightweight pass/fail
# ═══════════════════════════════════════════════════════════════════════

VALID_DML_OPERATIONS = ("insert", "update", "delete", "upsert")
SOBJECT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(__c|__mdt|__e|__b|__x)?$")

PII_PATTERNS = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "Credit card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    "Personal email": re.compile(
        r"\b[A-Za-z0-9._%+-]+@(gmail|yahoo|hotmail|outlook|aol)\.(com|net|org)\b",
        re.IGNORECASE,
    ),
}


def validate_data_params(input_data: dict[str, Any]) -> dict[str, Any]:
    """Validate soql_query or sobject_dml parameters.

    Returns a simple pass/fail with lists of errors and warnings.
    No scoring — just binary checks for things that would fail or leak data.

    Args:
        input_data: Dict with keys "tool", "params", and optional "context".

    Returns:
        {
            "tier": "data_params",
            "tool": "soql_query" | "sobject_dml",
            "status": "pass" | "fail",
            "errors": [ {"message": "..."} ],
            "warnings": [ {"message": "..."} ]
        }
    """
    tool = input_data.get("tool", "")
    params = input_data.get("params", {})

    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    # ── Shared checks ───────────────────────────────────────────────
    if not params.get("sObject"):
        errors.append({"message": "Missing required 'sObject' parameter"})
    elif isinstance(params.get("sObject"), str) and not SOBJECT_NAME_PATTERN.match(params["sObject"]):
        warnings.append({"message": f"sObject name '{params['sObject']}' doesn't match expected pattern"})

    if not params.get("sf_user"):
        warnings.append({"message": "No 'sf_user' specified — will use default org connection"})

    # ── soql_query checks ───────────────────────────────────────────
    if tool == "soql_query":
        where = params.get("whereClause") or ""
        if where.strip():
            _check_where_syntax(where, warnings)

    # ── sobject_dml checks ──────────────────────────────────────────
    elif tool == "sobject_dml":
        operation = params.get("operation", "")
        records = params.get("records", [])
        record_ids = params.get("recordIds", [])
        ext_id_field = params.get("externalIdField")

        # Valid operation
        if operation not in VALID_DML_OPERATIONS:
            errors.append({
                "message": f"Invalid operation: '{operation}'. "
                           f"Expected one of: {', '.join(VALID_DML_OPERATIONS)}"
            })

        # Delete uses recordIds (string array), not records
        if operation == "delete":
            if not isinstance(record_ids, list) or len(record_ids) == 0:
                # Fall back to checking records for backward compat
                if not isinstance(records, list) or len(records) == 0:
                    errors.append({"message": "Delete requires 'recordIds' (string array of Ids)"})
                else:
                    if len(records) > 200:
                        errors.append({
                            "message": f"Too many records ({len(records)}). "
                                       f"MCP server limit is 200 per call — split into batches"
                        })
                    missing_id = [
                        i for i, r in enumerate(records)
                        if isinstance(r, dict) and "Id" not in r
                    ]
                    if missing_id:
                        errors.append({
                            "message": f"{len(missing_id)} record(s) missing 'Id' field "
                                       f"for {operation} operation"
                        })
                    warnings.append({
                        "message": "Delete should use 'recordIds' parameter (string array) "
                                   "instead of 'records' — e.g. recordIds=[\"001xx...\", \"001yy...\"]"
                    })
            elif len(record_ids) > 200:
                errors.append({
                    "message": f"Too many recordIds ({len(record_ids)}). "
                               f"MCP server limit is 200 per call — split into batches"
                })

        # Records array for non-delete operations
        elif not isinstance(records, list) or len(records) == 0:
            errors.append({"message": "Empty or missing records array"})
        else:
            # Check 200-record limit
            if len(records) > 200:
                errors.append({
                    "message": f"Too many records ({len(records)}). "
                               f"MCP server limit is 200 per call — split into batches"
                })

            # Update must have Id
            if operation == "update":
                missing_id = [
                    i for i, r in enumerate(records)
                    if isinstance(r, dict) and "Id" not in r
                ]
                if missing_id:
                    errors.append({
                        "message": f"{len(missing_id)} record(s) missing 'Id' field "
                                   f"for {operation} operation"
                    })

            # Upsert requires externalIdField
            if operation == "upsert" and not ext_id_field:
                errors.append({
                    "message": "Upsert operation requires externalIdField parameter"
                })

            # Upsert records must contain the external ID field
            if operation == "upsert" and ext_id_field:
                missing_ext = [
                    i for i, r in enumerate(records)
                    if isinstance(r, dict) and ext_id_field not in r
                ]
                if missing_ext:
                    warnings.append({
                        "message": f"{len(missing_ext)} record(s) missing external "
                                   f"ID field '{ext_id_field}'"
                    })

            # Inconsistent fields across records
            if operation == "insert" and len(records) >= 2:
                field_sets = [
                    frozenset(r.keys()) for r in records if isinstance(r, dict)
                ]
                if field_sets and len(set(field_sets)) > 1:
                    warnings.append({
                        "message": "Inconsistent field names across records — "
                                   "some records have different fields"
                    })

            # PII detection
            _check_pii(records, warnings)

    else:
        errors.append({
            "message": f"Tool '{tool}' is not a data operation. "
                       f"Expected 'soql_query' or 'sobject_dml'. "
                       f"For code deployment validation, use sf-apex "
                       f"or sf-flow."
        })

    status = "fail" if errors else "pass"

    return {
        "tier": "data_params",
        "tool": tool,
        "status": status,
        "errors": errors,
        "warnings": warnings,
    }


def _check_where_syntax(where: str, warnings: list[dict[str, str]]):
    """Check for common SOQL syntax mistakes in whereClause."""
    if re.search(r"==", where):
        warnings.append({
            "message": "Invalid '==' operator in whereClause — SOQL uses '='"
        })
    if re.search(r'=\s*"[^"]*"', where):
        warnings.append({
            "message": "Double-quoted string in whereClause — SOQL uses single quotes"
        })
    if where.count("(") != where.count(")"):
        warnings.append({
            "message": "Unbalanced parentheses in whereClause"
        })


def _check_pii(records: list, warnings: list[dict[str, str]]):
    """Scan record values for PII patterns."""
    pii_found: dict[str, list[str]] = {}

    for i, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        for field, value in record.items():
            if not isinstance(value, str):
                continue
            for pii_type, pattern in PII_PATTERNS.items():
                if pattern.search(value):
                    if pii_type not in pii_found:
                        pii_found[pii_type] = []
                    pii_found[pii_type].append(f"record {i}, field '{field}'")
                    break  # one match per value is enough

    for pii_type, locations in pii_found.items():
        sample = locations[0]
        extra = f" (and {len(locations) - 1} more)" if len(locations) > 1 else ""
        warnings.append({
            "message": f"{pii_type} pattern detected in {sample}{extra} "
                       f"— use synthetic test data instead"
        })


# ═══════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════

class MCPDataValidator:
    """Validates data operation parameters for soql_query and sobject_dml.

    Usage:
        validator = MCPDataValidator()
        result = validator.validate({"tool": "soql_query", "params": {...}})
    """

    def validate(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Validate data operation parameters.

        Args:
            input_data: Dict with "tool", "params", optional "context".

        Returns:
            Pass/fail result with errors and warnings.
        """
        return validate_data_params(input_data)
