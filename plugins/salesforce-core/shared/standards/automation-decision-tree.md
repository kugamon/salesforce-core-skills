# Automation Decision Tree

**Consult this BEFORE writing anything.** The most expensive automation is the
one that shouldn't exist. Walk the tree top-down; the first matching route
wins. Skills on both sides of the fence (sf-flow, sf-apex) share this tree —
neither tool is the default.

## Step 0: Should this be automated at all?

Do NOT automate when:

- **It runs once.** A one-time data fix is a data job (sf-data), not automation.
- **The rule is still changing weekly.** Let the process stabilize manually
  first; automating a moving target creates rework plus regression risk.
- **A human decision is the point.** Approval judgment calls, exception
  handling, relationship-sensitive actions — automate the routing, not the
  decision.
- **The trigger volume is trivial and the manual cost is lower** than the
  maintenance cost of one more piece of org automation.

If any of these hold, stop and tell the user why.

## Step 1: Can the platform do it with zero custom automation (OOTB)?

| Need | Route |
| --- | --- |
| Derived value, same record, recalculated on read | **Formula field** — no automation, no tests, no limits |
| SUM / COUNT / MIN / MAX of children on master-detail | **Roll-up summary field** |
| Block bad data at save | **Validation rule** |
| Prevent duplicates | **Duplicate rules + matching rules** |
| Simple field default | **Default value on the field** |
| Assignment/routing of leads or cases | **Assignment rules** (consider before flow) |
| Approval with simple single-step chain | **Approval process** (see sf-flow's engine-choice section) |

Formula/rollup beats *any* flow or trigger for pure derivation: no execution
order, no recursion, no test classes, always consistent. Only fall through
when the value must be stamped (reportable snapshots, cross-object where no
master-detail exists, or formula limits are hit).

## Step 2: Declarative or code? (Flow vs Apex)

Route to **record-triggered Flow** (sf-flow) when ALL of these hold:

- Logic touches the triggering record and at most 1–2 levels of related
  records reachable via `$Record` traversal or a single Get Records
- No loops over large related-record collections with per-record math
- Branching is expressible in a handful of Decision elements (rule of thumb:
  ≤ ~5 branches, ≤ ~2 nested levels)
- No callouts requiring complex retry/error semantics, no heavy transforms
- Admins should be able to read and maintain it

Route to **Apex trigger/handler** (sf-apex) when ANY of these hold:

- **Loops over related records with accumulation or bulk math** (recalc
  totals across children, cross-object reconciliation) — flows do this slowly
  and unreadably
- **Complex branching** — deep nesting, dynamic field references, polymorphic
  logic; a 40-element flow is worse than 40 lines of Apex
- **Ordering/recursion control matters** — multiple automations on one object
  needing deterministic sequence (one trigger + handler routing)
- **Shared logic** used by triggers AND LWC/API/batch — put it in a service
  class; a flow can't be called from everywhere
- **Governor-sensitive bulk paths** — 200-record chunks doing per-record
  queries/DML patterns that flows can't collect-then-execute cleanly
- Needs Queueable chaining, Batch, complex callouts, or the Stub/mock
  testability story

**Mixed is normal**: a thin flow calling an `@InvocableMethod` Apex action
gets declarative visibility with coded logic. Prefer it over a giant flow OR
over Apex nobody can see from Setup.

## Step 3: Before-save vs after-save (applies to both flow and trigger)

| Question | Yes → |
| --- | --- |
| Updating fields on the *triggering record only*? | **Before-save** (flow) / `before insert/update` (Apex). No extra DML, ~10x faster, no recursion re-fire |
| Creating/updating *other* records, sending email, callouts, async? | **After-save** (flow) / `after` contexts (Apex) — record Id exists, but every fallible element needs fault handling (see sf-flow's save-blocking rule) |
| Blocking the save on a condition? | Validation rule first; before-save with error only when the rule can't express it |

## Step 4: One-object sanity check

Before adding automation to an object, inventory what's already there
(triggers, record-triggered flows, workflow rules, process builders). More
than one automation family on the same object+event is a maintenance and
ordering hazard — consolidate toward one trigger-handler (see
`../templates/TriggerHandler.cls`) or one orchestrating flow rather than
adding a competing runner.

## Cross-references

- Async pattern choice (once Apex is the answer): `async-decision-tree.md`
- Sharing/security context of the automation: `sharing-model-decision-tree.md`
- Flow-side guardrails and fault routing: sf-flow SKILL.md
- Apex-side guardrails and 150-point rubric: sf-apex SKILL.md
