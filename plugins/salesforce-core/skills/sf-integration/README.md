# sf-integration

Set up and review Salesforce integrations — Named/External Credentials, OAuth flow selection, Platform Events, and Change Data Capture — MCP-first against the live org, with a hard rule that secrets never transit chat.

## What it does

| Action | Description |
| --- | --- |
| `credentials` | External Credential + Named Credential shells (Metadata API path), principal design, permission-set access grant, migration from legacy credentials and Remote Site Settings — secrets entered by the admin in Setup, never through the skill |
| `events` | Platform event definition, publish/subscribe patterns, EventBusSubscriber monitoring, replay-ID semantics, stalled-subscriber diagnosis |
| `cdc` | Change Data Capture enablement, change-event subscriber patterns, gap/overflow-event and changed-fields gotchas |
| `review` | Inventory RemoteSiteSettings + NamedCredentials + ExternalCredentials, flag remote sites that should be credentials, produce a prioritized migration table |

OAuth flow selection (client credentials vs JWT bearer vs authorization code) ships as a decision table in references, with sf-diagram drawing the chosen flow.

## Examples

- "Set up a named credential for the Stripe API — which OAuth flow should we use?"
- "Our platform event trigger stopped processing events but shows no errors"
- "Audit this org's integrations — we still have a pile of remote site settings"

## License

MIT License — see [LICENSE](LICENSE) for details. For credits see [CREDITS](CREDITS.md).
