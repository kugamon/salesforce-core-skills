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

## Step-by-step: fork, branch, PR

New to GitHub contributions? The full path:

```sh
# 1. Fork this repo on github.com (Fork button, top right), then clone YOUR fork
git clone https://github.com/<your-username>/salesforce-core-skills.git
cd salesforce-core-skills
git remote add upstream https://github.com/kugamon/salesforce-core-skills.git

# 2. Branch
git checkout -b fix-sf-apex-managed-bodies

# 3. Make your changes, then validate before committing
python3 scripts/validate_skills.py

# 4. Commit and push to your fork
git add .
git commit -m "fix(sf-apex): skip managed bodies in the inventory query"
git push origin fix-sf-apex-managed-bodies
```

GitHub then shows a **Compare & pull request** button on your fork — click it to open the PR against `kugamon/salesforce-core-skills` `main`.

**PR titles follow [Conventional Commits](https://www.conventionalcommits.org/)** and are checked by CI: `<type>(<scope>): <description>` where type is one of build, chore, ci, docs, feat, fix, perf, refactor, revert, style, test, and scope is usually a skill name. Examples: `feat(sf-orgdiff): add package-version comparison`, `fix(sf-apex): validator no longer scores managed bodies`, `docs: clarify headless approval rules`. Append `!` before the colon for breaking changes.

To keep your fork current: `git fetch upstream && git rebase upstream/main`.

## PR checklist (also enforced by the PR template)

- [ ] `scripts/validate_skills.py` passes locally
- [ ] New/changed skills keep the Tool-name mapping convention (no literal connector tool names in workflows)
- [ ] evals.json updated for new skills
- [ ] No secrets, org identifiers, or customer data anywhere (sample data must be synthetic)
- [ ] Version bumped in both manifests if behavior changed
- [ ] PR title follows Conventional Commits (CI enforces it)

## Releases (automated)

Merges to `main` that touch `plugins/**`, `sample-data/**`, `scripts/**`, or `evals/evals.json` trigger the release workflow. It reads the Conventional Commit titles since the last tag and decides:

| Commit types since last tag | Result |
| --- | --- |
| `feat` | minor bump (2.1.0 → 2.2.0) |
| `fix`, `perf`, `refactor` | patch bump (2.1.0 → 2.1.1) |
| `!` or `BREAKING CHANGE` in the body | major bump (2.1.0 → 3.0.0) |
| only `docs`, `chore`, `ci`, `style`, `test`, `build` | **no release** — they ride along in the next real one |

The workflow validates the repo, bumps both manifests, updates the changelog, tags, and publishes release notes grouped by type — so commit titles are the release notes. Write them for the person reading the release, not for yourself.

Preview without releasing: Actions → Release → Run workflow (dry run is the default), or locally:

```sh
python3 scripts/release_version.py --dry-run
```

## License

Contributions are accepted under the repo's MIT license. Portions of this project derive from MIT-licensed work with preserved attributions — keep CREDITS.md files accurate.
