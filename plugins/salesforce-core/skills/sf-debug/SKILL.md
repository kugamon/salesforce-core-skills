---
name: sf-debug
plugin: salesforce-core
argument-hint: '[trace|logs|analyze|limits] {user|class|logId} ...'
metadata:
  version: 1.0.0
description: >
  Captures and analyzes Salesforce debug logs through the Tooling API — trace
  flag setup, log retrieval, parsing for exceptions, SOQL-in-loop detection,
  CPU/heap/limit analysis, and row-lock diagnosis — all MCP-first against the
  live org. Use when the user hits an error in Salesforce, mentions debug logs,
  governor limits, "too many SOQL queries", CPU timeouts, UNABLE_TO_LOCK_ROW,
  flow errors, or asks why something failed in the org.
  Usage: /sf-debug [trace|logs|analyze|limits] {user|class|logId} ...
---

# Salesforce Debug Log Capture & Analysis

Debugging specialist for live Salesforce orgs. Set up tracing, capture the
failure, read the log so the user doesn't have to, and hand back a diagnosis
with the fix — not a wall of log lines.

## Dispatch

| First argument or intent                             | Workflow       |
| ---------------------------------------------------- | -------------- |
| `trace`, "turn on logging", "capture what happens"   | Set Up Tracing |
| `logs`, "get the logs", "latest log for X"           | Retrieve Logs  |
| `analyze`, a log ID/file, "why did this fail"        | Analyze Log    |
| `limits`, "governor limits", "CPU/heap usage"        | Limit Analysis |
| An error message pasted with no other context        | Triage (below) |

**Triage:** when the user pastes an error, classify first via
`references/common-errors.md` — many errors (validation rule text, duplicate
rules, flow fault emails) identify themselves without needing a log capture.
Only set up tracing when the cause genuinely needs execution detail.

## Execution modes

See `references/execution-modes.md`. This skill is inherently live-org:
Tooling API via MCP in every mode (`cli` mode may use `sf apex tail log` as
a convenience). Initialize the connection first (`org_init` convention).

---

## Set Up Tracing

1. **Identify the traced entity** — a user (most common), the Automated
   Process user (flows/platform events), or a platform integration user.
   Resolve the user ID via SOQL.
2. **Create or reuse a DebugLevel** (Tooling DML). Default profile:

   | Category   | Level  | Why |
   | ---------- | ------ | --- |
   | ApexCode   | FINE   | Method entry/exit without FINEST's noise |
   | ApexProfiling | INFO | Limit snapshots |
   | Database   | INFO   | SOQL/DML with row counts |
   | Workflow   | INFO   | Flow/process elements |
   | Callout    | INFO   | Request/response boundaries |
   | System     | DEBUG  | System.debug output |
   | Validation | INFO   | Rule evaluations |

   Escalate to FINEST (ApexCode) only for method-level CPU hunts — FINEST
   logs hit the 20 MB truncation limit fast in busy transactions.
3. **Create the TraceFlag** (Tooling DML): `TracedEntityId`, `DebugLevelId`,
   `LogType='USER_DEBUG'`, `ExpirationDate` ≤ 30 minutes out. Short
   expirations are deliberate — abandoned trace flags fill org log storage
   (250 MB cap) and then NOTHING logs.
4. **Tell the user to reproduce** the failure, or reproduce it yourself via
   `apex_execute` when the repro is scriptable (safe, non-mutating repros
   only in production — prefer sandboxes for anything that writes).
5. **Clean up afterward** — delete the TraceFlag when analysis is done.
   Always. This is the debugging equivalent of removing the tourniquet.

## Retrieve Logs

Query, newest first:

```sql
SELECT Id, LogUser.Name, Operation, Request, Status, LogLength,
       DurationMilliseconds, StartTime
FROM ApexLog ORDER BY StartTime DESC LIMIT 10
```

Filter by `LogUserId`, `Operation` (e.g. `/apex/...`, `API`,
`BatchApexWorker`), or `Status != 'Success'` as context demands. Fetch the
body via the MCP REST tool: `GET /services/data/vXX.X/tooling/sobjects/ApexLog/{Id}/Body`.

Logs over ~2 MB: don't read linearly. In code-execution modes, save to a file
and extract the interesting sections with the parsing patterns below; in
mcp-only mode, fetch and scan in chunks prioritizing the end of the log
(exceptions and limit summaries cluster there).

## Analyze Log

Work the log in this order — it's diagnostic priority, not file order:

1. **Fatal errors first:** search `FATAL_ERROR`, `EXCEPTION_THROWN`,
   `FLOW_ELEMENT_ERROR`. The LAST exception is usually the reported one; the
   FIRST is usually the cause.
2. **Limit summary:** `LIMIT_USAGE_FOR_NS` blocks (per namespace). Compare
   each meter to its ceiling — see Limit Analysis table.
3. **SOQL-in-loop signature:** repeated `SOQL_EXECUTE_BEGIN` with the same
   query text and climbing aggregate count, typically interleaved with
   `METHOD_ENTRY` of the same method. Same pattern for `DML_BEGIN` = DML in
   loop. This is the #1 finding in real logs — report the query, the loop
   method, and the row counts.
4. **CPU hotspots:** with ApexProfiling, use `CUMULATIVE_PROFILING` blocks;
   without it, bracket `CODE_UNIT_STARTED/FINISHED` timestamps to find the
   expensive unit. Flow-heavy transactions: count `FLOW_ELEMENT_BEGIN` —
   loops over collections in flows burn CPU invisibly.
5. **Lock diagnosis:** `UNABLE_TO_LOCK_ROW` — identify the contested record
   from the DML context, then look for the competing transaction type
   (batch + trigger on the same parent is the classic). See
   `references/common-errors.md` for the resolution matrix.
6. **Callout timeline:** `CALLOUT_REQUEST/RESPONSE` pairs — long gaps are
   external latency, not org problems; say so explicitly.

**Output format** — always this shape:

```
## Diagnosis
<one-paragraph root cause>

## Evidence
<log line numbers/timestamps + the meters or exceptions that prove it>

## Fix
<specific change, with a handoff to sf-apex/sf-flow/sf-test when code changes>

## Prevention
<the limit/pattern to watch, monitoring suggestion if warranted>
```

## Limit Analysis

Reference ceilings (synchronous / asynchronous):

| Limit | Sync | Async | Log marker |
| --- | --- | --- | --- |
| SOQL queries | 100 | 200 | `Number of SOQL queries` |
| SOQL rows | 50,000 | 50,000 | `Number of query rows` |
| DML statements | 150 | 150 | `Number of DML statements` |
| DML rows | 10,000 | 10,000 | `Number of DML rows` |
| CPU time | 10,000 ms | 60,000 ms | `Maximum CPU time` |
| Heap | 6 MB | 12 MB | `Maximum heap size` |
| Callouts | 100 | 100 | `Number of callouts` |
| Future calls | 50 | 0 in future ctx | `Number of future calls` |

Report meters above 60% as warnings and above 85% as critical even when the
transaction succeeded — today's 87% is next month's limit exception when the
data grows. For recurring analysis across many transactions, offer an
org-wide pass: query recent `ApexLog` rows, extract limit blocks in a code
loop, and present the top offenders by operation.

## Cross-skill handoffs

- Bulkification / CPU fixes → **sf-apex** (its 150-point rubric covers the
  patterns); flow element fixes → **sf-flow**
- Failing tests captured in logs → **sf-test**
- Systemic slow queries → **sf-data** (query optimization)

## References

| File | Read when |
| --- | --- |
| `references/common-errors.md` | Triage — error classification and resolution matrix |
| `references/execution-modes.md` | Start of session |
