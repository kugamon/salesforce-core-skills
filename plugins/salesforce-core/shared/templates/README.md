# Shared Templates

Real, copyable starting files shared across the salesforce-core skills. Copy
into the target org (adapting object names and defaults), don't reinvent.

| File | What it is | When to copy it | Governing skill |
| --- | --- | --- | --- |
| `TriggerHandler.cls` | Dependency-free one-trigger-per-object handler base class (context routing, bypass flag, recursion guard) | Org needs trigger structure but the Trigger Actions Framework is overkill or a package dependency is unwanted | sf-apex |
| `AccountTrigger.trigger` | One-line-body example trigger wiring for TriggerHandler | Alongside TriggerHandler, once per object (rename object + handler) | sf-apex |
| `TestDataFactory.cls` | Test data factory with make (unsaved) / create (inserted) variants and a required-field defaults hook | First test class in an org, or when 3+ test classes duplicate data setup | sf-test |
| `Logger.cls` | Minimal System.debug logger with severity + per-transaction correlation id, pluggable sink comment | Org has NO logging framework — if Nebula Logger etc. is installed, use that instead | sf-debug |

Decision trees that decide whether these files are needed at all live in
`../standards/` (automation, async, sharing-model).
