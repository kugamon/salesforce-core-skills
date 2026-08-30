# Behavioral Evals

Structural CI (`scripts/validate_skills.py`) proves the repo is well-formed. **Behavioral evals prove the skills actually work** — every skill is exercised end-to-end against a live Salesforce dev org by an independent agent run, graded against the expectations in `evals.json`, with results published in `results/`.

## Methodology

1. **One eval per skill** (`evals.json`): a realistic user prompt plus an `expect` array of observable behaviors. Prompts are what a real admin/developer would type, not test jargon.
2. **Independent runs.** Each eval runs as a fresh subagent that reads the skill and executes the prompt — the runner is not the author. Runs are batched: org-read, org-write, analysis.
3. **Org safety.** Runs target a disposable dev org, never production. Write evals create uniquely-named artifacts and MUST delete them and verify zero rows afterward; the org gets a final residue sweep. Read evals are read-only by instruction and by the guardrail hooks.
4. **Grading.** A separate grader reads each run's deliverables and run-notes, marks every expectation PASS / PARTIAL / FAIL / N/A(environment) with cited evidence, assigns a verdict (WORKING / WORKING-WITH-ISSUES / BROKEN), and aggregates a ranked fix backlog.
5. **Fix and iterate.** Every defect becomes a fix; the next iteration re-runs all evals and explicitly verifies each fix (see iteration-2's 8/8 fix-verification table). Iterations ship in `results/iteration-N/` (eval-report.md + grading.json).

## Running an iteration yourself

You need: this repo, a Salesforce MCP connector to a **dev org you can write to**, and an agent runtime with subagents (Claude Code / Cowork). For each entry in `evals.json`, run the prompt with the skill loaded, save deliverables + run-notes, then grade against `expect`. Keep the write-cleanup discipline — an eval that leaves residue is itself a failed eval. PRs adding your iteration results are welcome (redact org identifiers).

## History

| Iteration | Skills version | Result |
| --- | --- | --- |
| [iteration-1](results/iteration-1/eval-report.md) | v1.3.0 | 11 WORKING, 2 WORKING-WITH-ISSUES, 0 BROKEN — 31/38 expectations; findings fixed in v1.3.1 |
| [iteration-2](results/iteration-2/eval-report.md) | v1.4.x | 33/39 expectations, 0 FAIL, 12/13 runs improved; 8/8 fixes verified; residuals fixed in v1.5.1 |
