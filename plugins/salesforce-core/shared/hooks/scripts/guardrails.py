#!/usr/bin/env python3
"""
Always-on guardrails for Salesforce MCP writes (PreToolUse hook).

Three checks, all ADVISORY (never block — they add context so the agent
and user see the risk before the write lands):

  G1  SOQL/DML inside loops in Apex bodies (classic governor-limit bug)
  G2  High-risk permission grants (ModifyAllData, AuthorApex, ...)
  G3  Broad destructive DML (large delete batches / unscoped delete intent)

Reads Claude Code hook input on stdin; emits hookSpecificOutput JSON.
"""
import json, re, sys

HIGH_RISK_PERMS = [
    "ModifyAllData", "ViewAllData", "AuthorApex", "ManageUsers",
    "AssignPermissionSets", "ResetPasswords", "ManageInternalUsers",
    "CustomizeApplication", "ManageIpAddresses", "ApiUserOnly",
]

LOOP_RE = re.compile(r"\b(for|while)\s*\(", re.I)
SOQL_DML_RE = re.compile(r"(\[\s*SELECT\b|\binsert\s+\w|\bupdate\s+\w|\bdelete\s+\w|\bupsert\s+\w|Database\.(query|insert|update|delete|upsert)\()", re.I)


def find_loop_soql(body: str):
    """Heuristic: report SOQL/DML that appears inside a loop's brace block."""
    hits = []
    for m in LOOP_RE.finditer(body):
        # find the loop's opening brace, then scan its balanced block
        i = body.find("{", m.end())
        if i < 0:
            continue
        depth, j = 1, i + 1
        while j < len(body) and depth:
            if body[j] == "{":
                depth += 1
            elif body[j] == "}":
                depth -= 1
            j += 1
        block = body[i:j]
        dm = SOQL_DML_RE.search(block)
        if dm:
            line = body[: m.start()].count("\n") + 1
            hits.append(f"loop at line ~{line} contains {dm.group(0).strip()[:40]!r}")
    return hits


def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}))
        return
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}
    base = tool.split("__")[-1]
    warnings = []

    payload_text = json.dumps(ti)

    # G1 — Apex bodies in metadata/tooling writes
    if base in ("metadata_create", "metadata_update", "tooling_api_dml", "apex_execute"):
        for s in walk_strings(ti):
            if len(s) > 120 and ("class " in s or "trigger " in s or "void " in s):
                for h in find_loop_soql(s):
                    warnings.append(f"G1 SOQL/DML-in-loop: {h}")

    # G2 — permission escalation
    if base in ("metadata_create", "metadata_update", "tooling_api_dml", "update_record", "create_record"):
        granted = [p for p in HIGH_RISK_PERMS if re.search(p + r'\D{0,24}?(true|"enabled"\s*:\s*true)', payload_text)]
        if granted:
            warnings.append(f"G2 high-risk permission grant(s): {', '.join(granted)} — confirm least-privilege intent with the user")

    # G3 — broad destructive DML
    if base in ("sobject_dml", "bulk_delete_records", "tooling_api_dml", "delete_record"):
        op = str(ti.get("operation", "")).lower() or ("delete" if "delete" in base else "")
        recs = ti.get("records") or ti.get("record_ids") or []
        if "delete" in op:
            n = len(recs) if isinstance(recs, list) else 0
            if n > 200:
                warnings.append(f"G3 destructive DML: deleting {n} records in one call — confirm scope and backup/rollback plan")
            elif n == 0:
                warnings.append("G3 destructive DML with no explicit record list — verify the target set is bounded before executing")

    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}
    if warnings:
        out["hookSpecificOutput"]["additionalContext"] = (
            "GUARDRAILS (advisory): " + " | ".join(warnings)
            + " — Address or consciously accept each before proceeding; tell the user about any you accept."
        )
    print(json.dumps(out))


if __name__ == "__main__":
    main()
