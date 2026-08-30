# Security Policy

## Reporting

If you find a security issue in these skills — a workflow that could leak credentials, a guardrail bypass, a validator that under-reports a dangerous pattern, or sample data that isn't synthetic — email **info@kugamon.com** with details. Please don't open a public issue for anything exploitable; we'll acknowledge within a few business days.

## Scope

- **Skills never handle secrets.** No skill may accept, echo, or store client secrets, tokens, private keys, or passwords; credential setup hands off to the Salesforce Setup UI (see sf-integration's security discipline). A skill that violates this is a security bug.
- **Guardrails** (`shared/hooks/scripts/guardrails.py`) block high-risk permission grants and unbounded destructive DML behind explicit confirmation. Bypasses or false negatives in G1–G3 are security bugs.
- **Read-only means read-only.** sf-orgdiff and the reviewer agents (`agents/`) are read-only by contract; any write path from them is a security bug.
- These skills instruct an AI agent operating against orgs you connect. Review what any agent does in production orgs; prefer sandboxes. The skills' own rules (approval gates, propose-only headless writes) are guardrails, not guarantees.
