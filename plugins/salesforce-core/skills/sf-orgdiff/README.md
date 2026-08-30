# sf-orgdiff

Compare two connected Salesforce orgs through their MCP connectors —
inventory-first metadata diffing with severity-ranked drift reports.
Strictly read-only on both orgs; both identities verified before a single
comparison query runs.

## What it does

| Action | Description |
| --- | --- |
| `drift` | Sandbox ↔ production ongoing drift: what's pending deployment (source-newer) vs hotfix drift (prod-only — the kind the next deploy overwrites) |
| `release` | Pre/post-deploy verification: did every item in the release land in the target, at the right version, with flows *active* |
| `baseline` | Org vs reference org (e.g. customer vs demo): missing/modified reference items and package-version gaps, customer customizations inventoried neutrally |

All modes diff inventories first (names, versions, `LengthWithoutComments`,
field counts, package versions) and fetch bodies only for the unmanaged
both-but-different shortlist. Managed packages are compared by version,
never by contents. Output is a drift report: per-domain summary table,
detail tables with the actionable read, attention flags, and a
reconciliation plan handed to sf-metadata.

## Examples

- "What drifted between the my-sandbox org and production?"
- "We deployed release 2.4 yesterday — did everything land in production?"
- "Compare the customer's org against our demo baseline, apex and flows only"

## License

MIT License — see [LICENSE](LICENSE) for details. For credits see [CREDITS](CREDITS.md).
