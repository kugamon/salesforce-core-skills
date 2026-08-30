<!-- PR title must follow Conventional Commits: <type>(<scope>): <description> — e.g. feat(sf-orgdiff): add package-version comparison. CI checks this. -->

## What & why

## Checklist
- [ ] `python3 scripts/validate_skills.py` passes
- [ ] Tool names remain conventions (no literal connector tool names in workflows)
- [ ] `evals/evals.json` updated if skills were added
- [ ] No secrets / org identifiers / non-synthetic data
- [ ] Manifests version-bumped if behavior changed
- [ ] For validator/script changes: before/after self-test evidence in the PR description
