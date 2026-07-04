---
name: sf-test
plugin: salesforce-core
argument-hint: '[generate|review|run] [class|all] {name} ...'
metadata:
  version: 1.0.0
description: >
  Generates, reviews, and runs Salesforce Apex test classes with a 120-point
  test-quality scoring rubric using a Salesforce MCP server. Use when writing
  test classes, improving code coverage, reviewing existing tests for assertion
  quality and bulk safety, running test suites, or diagnosing coverage gaps
  before a deployment or AppExchange submission.
  Usage: /sf-test [generate|review|run] [class|all] {name} ...
---

# Salesforce Apex Test Generation, Review, and Execution

Expert Apex test engineer. Generate meaningful tests — not coverage padding —
with proper isolation, bulk safety, permission awareness, and assertions that
would actually catch regressions. Deploy and run via a Salesforce MCP server.

## Dispatch

Parse `$ARGUMENTS` to determine which workflow to run:

| First argument or intent                      | Workflow      |
| --------------------------------------------- | ------------- |
| `generate`, "write tests for X"               | Generate Tests |
| `review`, "score my tests", "are these good"  | Review Tests  |
| `run`, "run the tests", "what's my coverage"  | Run Tests     |
| No argument                                   | Ask which workflow; if a class name is given, default to Generate |

## Execution modes

Detect the execution mode once per session — see
`references/execution-modes.md`. In `sfdx-repo` mode, read classes from disk;
otherwise fetch via MCP. Initialize the org connection first (`org_init` — your
MCP server's session-init step; if none exists, verify with
`SELECT Id FROM Organization LIMIT 1`).

---

## Generate Tests

### Phase 1: Understand the code under test

1. Fetch the target class/trigger body (Tooling API query on `ApexClass` /
   `ApexTrigger`, or read from disk in `sfdx-repo` mode).
2. Map the surface: public/global methods, `@AuraEnabled`, `@InvocableMethod`,
   `@future`, Queueable/Batchable/Schedulable interfaces, callouts
   (`Http`, `HttpRequest`, named credentials), DML and SOQL operations,
   custom exceptions, and branching logic.
3. Fetch dependencies that affect test data: required fields, validation
   rules, and record types on the objects touched (`sobject_describe` /
   metadata read). Tests fail in real orgs because of validation rules the
   generator never saw — check them up front.

### Phase 2: Design the test plan

Build a test matrix BEFORE writing code. Cover every row that applies:

| Dimension        | What to include                                                    |
| ---------------- | ------------------------------------------------------------------ |
| Positive path    | Each public method's happy path with realistic data                |
| Negative path    | Invalid inputs, empty lists, nulls, exception branches asserted via try/catch or `Assert.fail()` sentinel |
| Bulk             | 200-record operations through the same code path                   |
| Permissions      | `System.runAs()` with a minimally-privileged user where the code enforces CRUD/FLS or sharing |
| Async            | `Test.startTest()/stopTest()` to flush futures/queueables; `Test.getEventBus().deliver()` for platform events |
| Callouts         | `HttpCalloutMock` / `WebServiceMock` implementations per external call |
| Boundary         | Governor-relevant sizes, date boundaries, recursion guards          |

Present the matrix to the user when scope is ambiguous; otherwise proceed.

### Phase 3: Generate the test class

Rules that make tests worth having:

- **One test class per production class**, named `<ClassName>Test`.
  `@IsTest` annotation, `private`, API version matching the class under test.
- **`@TestSetup` for shared data**; a `TestDataFactory` pattern
  (see `references/test-patterns.md`) when 3+ test classes need the same
  objects. Never `SeeAllData=true` unless testing something that genuinely
  requires org data (document why in a comment).
- **Modern `Assert` class** (`Assert.areEqual`, `Assert.isTrue`,
  `Assert.fail`) with a message on every assertion explaining what broke.
  Every test method asserts something meaningful — method-ran-without-error
  is not a test.
- **`Test.startTest()/stopTest()`** around the action under test only — not
  around data setup — so governor limits reset where it matters and async
  work flushes.
- **Bulk test proves bulkification**: build 200 records, run the path, assert
  on ALL results (not just the first record), and keep it under limits.
- **runAs tests prove security**: create a user with a minimal profile or
  permission set, `System.runAs()` the restricted path, assert the
  enforcement (exception or stripped fields) actually happens.
- **No dependencies between test methods.** Each method stands alone.

### Phase 4: Deploy

Deploy the test class via the MCP metadata tool (`metadata_create` /
`metadata_update` equivalents). On compile errors, fix and redeploy — common
causes are missing required fields on test data (re-check Phase 1 findings)
and API-version mismatches.

### Phase 5: Run and report

Run the new tests (see Run Tests below), then report: pass/fail per method,
coverage delta on the class under test, and the test-quality score
(see Scoring). Flag any class still below 75% coverage — the deployment
minimum — and below 85%, the recommended bar for AppExchange submissions.

---

## Review Tests

Score one or more existing test classes against the 120-point rubric.

1. Fetch the test class body plus the production classes it covers.
2. Evaluate each rubric category (below); cite line-level evidence for every
   deduction — "no message on Assert at line 42", not "assertions could be
   better".
3. Output a scored report:

| Test class | Score | %  | Verdict | Top issues |
| ---------- | ----- | -- | ------- | ---------- |
| FooTest    | 96/120 | 80% | ✅ Pass | No runAs coverage; 2 assert-free methods |

Threshold: 80/120 (67%) passes; below that, list the remediation plan in
priority order (missing assertions first — they're the cheapest fix with the
highest regression-catching value).

## Test-Quality Scoring (120 points)

| Category                  | Points | What earns them                                                        |
| ------------------------- | ------ | ---------------------------------------------------------------------- |
| Assertion quality         | 25     | Every method asserts outcomes with messages; negative paths assert exceptions; no assert-free methods |
| Data setup & isolation    | 20     | @TestSetup / factory pattern; no SeeAllData; required fields handled; no inter-test dependencies |
| Bulk & governor safety    | 20     | 200-record path exercised; assertions over the full set; startTest/stopTest placed correctly |
| Coverage breadth          | 20     | All public methods + branches; boundary cases; not just the happy path |
| Permission & sharing      | 15     | runAs with restricted user where code enforces security; both allow and deny asserted |
| Async & callout handling  | 15     | Mocks for every callout; async flushed and results asserted; platform events delivered |
| Structure & naming        | 5      | <ClassName>Test naming; one concern per method; readable arrange-act-assert |

Scoring notes: a test class with high line coverage but weak assertions caps
at 60/120 — coverage without assertions is the most expensive false comfort
in Salesforce development, and the rubric is deliberately built to punish it.

---

## Run Tests

MCP-first execution via the Tooling API (works in every execution mode; in
`cli` mode `sf apex run test` is the alternate path):

1. **Queue the run** — Tooling API `runTestsAsynchronous` with the test class
   IDs, or insert an `ApexTestQueueItem` per class via Tooling DML.
2. **Poll status** — `SELECT Id, Status, ApexClassId FROM ApexTestQueueItem
   WHERE ParentJobId = '<jobId>'` until all rows are `Completed`, `Failed`,
   or `Aborted`.
3. **Fetch results** — `SELECT Outcome, MethodName, Message, StackTrace,
   ApexClass.Name, RunTime FROM ApexTestResult WHERE AsyncApexJobId =
   '<jobId>'`.
4. **Fetch coverage** — `SELECT ApexClassOrTrigger.Name, NumLinesCovered,
   NumLinesUncovered FROM ApexCodeCoverageAggregate WHERE
   ApexClassOrTrigger.Name IN (...)` (Tooling API).
5. **Report** — pass/fail table, failure messages with stack traces, coverage
   per class, org-wide coverage if requested. For failures, offer to hand off
   to `sf-debug` (log analysis) or `sf-apex` (fix the production code).

Never run tests you just generated against a production org without telling
the user — test runs consume async capacity and coverage recalculation can be
slow in large orgs. Prefer sandboxes when the user has one connected.

---

## Cross-skill handoffs

- Production code fixes or refactors → **sf-apex** (150-point rubric)
- Test failures needing log analysis → **sf-debug**
- Coverage strategy for an AppExchange submission → **sf-security**
  (review-readiness checklist includes the 75% bar and test quality)

## References

| File | Read when |
| --- | --- |
| `references/test-patterns.md` | Writing factories, mocks, async/event tests, runAs patterns |
| `references/execution-modes.md` | Start of session — detect mode |
