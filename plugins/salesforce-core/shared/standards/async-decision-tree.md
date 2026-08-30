# Async Decision Tree

The full routing table for asynchronous Apex. sf-apex's Async Decision Matrix
is the quick version; this file is the canonical tree with limits and
disqualifiers. Consult before choosing a pattern — the wrong async primitive
is a rewrite, not a refactor.

## Decision table

| If you need... | Use | Key limits / notes | Disqualifiers |
| --- | --- | --- | --- |
| Fire-and-forget from a trigger; escape mixed-DML (setup + non-setup objects in one transaction); simple callout after DML | `@future` | 50 calls/txn (250k/24h shared async limit); primitive or collection-of-primitive params ONLY; no return value, no chaining, no job Id to monitor | Needs SObject params, chaining, monitoring, or retry → Queueable |
| Complex async work with state, SObject params, chaining, or guaranteed cleanup | `Queueable` | 50 enqueues/txn (1 when already async); chain depth unlimited in prod (5 in dev/trial orgs); returns `AsyncApexJob` Id; `Transaction Finalizer` for post-run cleanup/retry even after limit exceptions; `AsyncOptions` dedup via `QueueableDuplicateSignature` | Millions of records → Batch. Zero state, primitive-only, and already trivial → `@future` is acceptable but Queueable is the modern default |
| Process large data volumes (10k → 50M records) in governed chunks | `Batch Apex` | Up to 50M records via `QueryLocator`; scope 1–2000 (default 200, each chunk = fresh limits); 5 concurrent batches/org, 100 holding in flex queue; `Database.Stateful` for cross-chunk state; chain the next job from `finish()` | Small record counts (< a few thousand) → Queueable is faster to start and simpler to test |
| Run something on a schedule (nightly sync, weekly digest) | `Schedulable` | 100 scheduled jobs/org; cron granularity = minutes; `execute()` should only enqueue/launch (Batch or Queueable) — never do the heavy work inline | Sub-minute or on-demand triggers → Platform Events or direct enqueue |
| Decouple publisher from subscribers; fan-out to multiple consumers; cross-transaction signaling; another mixed-DML escape | `Platform Events` | Publish behavior is per event definition: PublishAfterCommit (the default) rolls back with the transaction — no events are delivered if it fails; PublishImmediately fires even on rollback (logging/telemetry only); the mixed-DML escape works in both cases once the transaction commits; hourly publish limits by edition; subscriber trigger runs as Automated Process user (sharing/audit-field implications); retry via `EventBus.RetryableException` (max 9) | Guaranteed exactly-once processing or ordering across events — events are at-least-once, design idempotent subscribers |
| React to record changes without touching the source object's trigger stack | `Change Data Capture` (change event trigger) | Async, after-commit, batched (up to 2000 events); runs as Automated Process user; must enable CDC per object; carries changed fields + header only | Synchronous validation or same-transaction field stamping → before-save automation, not CDC |

## Tree form

1. **Is it really async?** Same-record field math belongs in before-save.
   Don't reach for async to dodge a design problem.
2. **Data volume ≥ tens of thousands of records?** → **Batch**.
3. **Time-driven?** → **Schedulable** wrapping a Batch/Queueable.
4. **Multiple independent consumers, or publisher must not know
   subscribers?** → **Platform Events** (or **CDC** if the "publisher" is
   simply a record change).
5. **Everything else** (callouts after DML, chained steps, SObject state,
   retry, monitoring) → **Queueable** (+ Finalizer for cleanup/retry).
6. **`@future`** only when the work is genuinely trivial, primitive-param,
   fire-and-forget — or you specifically need its mixed-DML escape in a
   one-liner. Treat it as legacy-adjacent; Queueable supersedes it.

## Cross-cutting rules

- **Never chain `@future` → `@future`** (illegal) and never enqueue more than
  1 Queueable from an async context (limit is 1 when already async).
- **Test pattern for every choice**: `Test.startTest()/stopTest()` forces
  async completion; platform events need `Test.getEventBus().deliver()` —
  see sf-test's patterns reference.
- **All async runs in system mode without a user context** — re-check
  sharing/FLS assumptions: `sharing-model-decision-tree.md`.
- If the request might not need Apex at all, back up one level:
  `automation-decision-tree.md`.
