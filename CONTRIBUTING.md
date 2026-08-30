# Contributing

Thanks for helping make this the most trustworthy Salesforce skills collection. The bar here is different from most skill repos: **every skill is behaviorally tested against a live org** ([evals/](evals/)), and contributions are expected to keep that true.

## Ground rules

1. **Read the house conventions first.** Skills follow a consistent shape: frontmatter (name matching the directory, `plugin: salesforce-core`, `argument-hint`, `metadata.version`, `metadata.minApiVersion`), a dispatch table, phased workflows, an execution-modes reference with the Tool-name mapping preamble, cross-skill handoffs, and per-skill README/CREDITS/LICENSE. Copy an existing skill's structure (sf-debug is a good model).
2. **Tool names are conventions, not literals.** Never hardcode a specific MCP server's tool names in workflow steps — write against the capability conventions documented in every skill's `references/execution-modes.md`.
3. **No fabrication, no vendor lock.** Skills must work against any Salesforce MCP server, handle managed-package orgs honestly (hidden bodies are N/A, never scored), and degrade predictably in headless runs.
4. **Validation must pass:** `python3 scripts/validate_skills.py` from the repo root — CI runs it on every PR. New skills need an entry in `evals/evals.json` (a realistic prompt + expected behaviors).
5. **Scoring rubrics need evidence.** If your skill scores things, every deduction must be itemizable with line-level evidence. Validators must fail (nonzero exit) on critical findings and never print quality adjectives beside a FAILED verdict.

## What makes a good contribution

- **Bug reports that become eval cases** — the issue template asks for the prompt, the org shape (managed-heavy? empty?), and what went wrong. Good reports get added to `evals/evals.json` and fixed against a live org.
- **New skills** in uncovered live-org admin/ops territory (check [docs/when-to-use-what.md](docs/when-to-use-what.md) — greenfield-dev topics belong in Salesforce's official library, not here).
- **Reference improvements** from real-org experience: connector quirks, API-version gotchas, managed-package realities.
- **Eval iterations** — run the methodology in [evals/README.md](evals/README.md) against your own dev org and report findings.

## PR checklist (also enforced by the PR template)

- [ ] `scripts/validate_skills.py` passes locally
- [ ] New/changed skills keep the Tool-name mapping convention (no literal connector tool names in workflows)
- [ ] evals.json updated for new skills
- [ ] No secrets, org identifiers, or customer data anywhere (sample data must be synthetic)
- [ ] Version bumped in both manifests if behavior changed

## License

Contributions are accepted under the repo's MIT license. Portions of this project derive from MIT-licensed work with preserved attributions — keep CREDITS.md files accurate.
