# Common Salesforce Errors — Triage & Resolution Matrix

Classify pasted errors here before setting up log capture. Many identify
themselves; capture logs only when the row says so.

## Errors that identify themselves (no log needed)

| Error | Cause | Resolution |
| --- | --- | --- |
| `FIELD_CUSTOM_VALIDATION_EXCEPTION: <text>` | Validation rule fired; the text is the rule's message | Find the rule by message text (Tooling: `ValidationRule`), decide bypass vs data fix |
| `REQUIRED_FIELD_MISSING: [<fields>]` | Named fields empty on insert/update | Supply fields; in tests, fix the data factory |
| `DUPLICATE_VALUE` / `DUPLICATES_DETECTED` | Unique field or duplicate rule | Identify the colliding record; adjust matching rule if false positive |
| `INSUFFICIENT_ACCESS_OR_READONLY` / `INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY` | Sharing/FLS/profile on the acting user or a referenced record | Check the ACTING user's access to the REFERENCED record (the cross-ref part is what people miss) |
| `ENTITY_IS_DELETED` | Operating on a deleted record (often stale ID in async work) | Requery before use in the async context |
| `INVALID_CROSS_REFERENCE_KEY` | Lookup points at wrong-type or nonexistent ID | Trace where the ID came from; often a hardcoded ID across orgs |
| `STORAGE_LIMIT_EXCEEDED` | Org data/file storage full | Storage cleanup — not a code problem |
| `STRING_TOO_LONG` | Value exceeds field length | Truncate or widen the field |

## Errors that need a log

| Error | Likely cause | What to look for in the log |
| --- | --- | --- |
| `System.LimitException: Too many SOQL queries: 101` | Query in a loop, or trigger recursion | SOQL-in-loop signature; `CODE_UNIT` re-entry for recursion; fix = bulkify (sf-apex) or add recursion guard |
| `Too many DML statements: 151` | DML in loop | Same pattern on `DML_BEGIN` |
| `Apex CPU time limit exceeded` | Inefficient loops, nested triggers/flows, giant collections | CPU meter + the code unit bracketing; flows count toward Apex CPU — check `FLOW_ELEMENT_BEGIN` density |
| `Too many query rows: 50001` | Unselective query, missing WHERE | The query text in `SOQL_EXECUTE_BEGIN`; fix selectivity (sf-data) |
| `UNABLE_TO_LOCK_ROW` | Two transactions locking same record/parent | The DML target + concurrent op type; resolutions below |
| `MIXED_DML_OPERATION` | Setup + non-setup objects in one transaction | The two DML targets; split with `System.runAs` block (tests) or async (runtime) |
| `System.CalloutException: You have uncommitted work pending` | DML before callout in same transaction | `DML_BEGIN` preceding `CALLOUT_REQUEST`; reorder or go async |
| `Regex too complicated` / heap errors on text | Processing huge text bodies | Heap meter; stream/chunk instead |
| `FATAL_ERROR Internal Salesforce.com Error` | Platform bug or edge case | Capture minimal repro; this one justifies a Salesforce case |

## UNABLE_TO_LOCK_ROW resolution matrix

| Contention pattern | Fix |
| --- | --- |
| Batch job + user edits on same records | Narrow batch scope query; schedule off-hours; `Database.executeBatch(job, smaller)` |
| Trigger updating parent of many children (rollups) | Reduce lock window — move rollup async; consider Big Objects/reporting instead of live rollup |
| Integration hammering same parent account | Serialize at the integration layer; retry with backoff on the client |
| Parallel @future/queueable touching shared records | Chain queueables instead of parallel futures |
| FOR UPDATE held across callout | Never do this; release before callout |

## Flow errors

Flow fault emails contain the element name and error — start there. In logs:
`FLOW_ELEMENT_ERROR` names the element; the interview GUID links multi-log
transactions. "Number of iterations exceeded" = loop over >2,000 items (move
to Apex); "Too many SOQL queries" inside flows = Get Records inside a loop
(the flow equivalent of SOQL-in-loop; restructure with collection filters or
hand to sf-flow).

## Async post-mortems (no trace flag was on)

The failure already happened and there's no log? Check:
- `AsyncApexJob` — status, `ExtendedStatus` (has the exception message),
  `NumberOfErrors` for batches
- `FlowInterview` paused/failed interviews
- Platform event subscribers: `EventBusSubscriber` `Position`/`Status` — a
  stalled position means the trigger is erroring silently
- Email logs / `EmailMessage` for send failures

`ExtendedStatus` on AsyncApexJob is the most under-used diagnostic field on
the platform — it often contains the full exception without any tracing.
