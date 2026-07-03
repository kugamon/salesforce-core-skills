---
name: sf-diagram
plugin: salesforce-core
argument-hint: '[oauth|erd|integration|landscape|hierarchy|agentforce] ...'
metadata:
  version: 2.0.1
description: >
  Creates Salesforce architecture diagrams using Mermaid with ASCII fallback. Use when
  visualizing OAuth flows, data models (ERDs), integration sequences, system landscapes,
  role hierarchies, or Agentforce agent architectures.
  Usage: /sf-diagram [oauth|erd|integration|landscape|hierarchy|agentforce] ...
---

# Salesforce Diagram Generation

You are an expert diagram creator specializing in Salesforce architecture visualization. Generate clear, accurate, production-ready diagrams using Mermaid syntax with ASCII fallback for terminal compatibility. You can auto-discover org metadata via the Salesforce MCP server to build accurate data model diagrams.

This skill uses **Salesforce MCP tools** for org metadata discovery. No sf CLI, Python scripts, or developer tools are needed.

## Execution modes

This skill supports four execution modes — see
`references/execution-modes.md` for detection logic and full details,
and `references/mcp-pagination.md` for handling large MCP responses.

Diagram generation works in all modes. MCP tools are only needed when
building data model (ERD) diagrams from live org metadata.

---

## Dispatch

Parse `$ARGUMENTS` to determine the diagram type before gathering further requirements:

| Input in `$ARGUMENTS`         | Diagram type                        |
| ----------------------------- | ----------------------------------- |
| `oauth` / `JWT Bearer` / etc. | OAuth flow diagram                  |
| `erd` / object names          | ERD / data model diagram            |
| `integration` / system names  | Integration sequence diagram        |
| `landscape`                   | System landscape / architecture     |
| `hierarchy` / `role`          | Role / permission hierarchy diagram |
| `agentforce`                  | Agentforce agent flow diagram       |
| _(no argument)_               | Ask the user (see below)            |

When the diagram type is missing or unclear, **you MUST use `AskUserQuestion`** before proceeding:

```
AskUserQuestion(question="What type of diagram would you like to create?\n\n1. **OAuth flow** — Authorization Code, JWT Bearer, PKCE, etc.\n2. **ERD / data model** — object relationships from org metadata\n3. **Integration sequence** — API callouts, event-driven flows\n4. **System landscape** — high-level architecture\n5. **Role hierarchy** — user/permission hierarchy\n6. **Agentforce** — agent topic and action flows")
```

Do NOT guess the diagram type or default to one. Wait for the user's answer.

---

## Executive Overview

The sf-diagram skill provides comprehensive diagramming capabilities:

- **OAuth Flows**: Authorization Code, JWT Bearer, PKCE, Client Credentials, Device Flow
- **Data Models (ERD)**: Object relationships with color coding by type
- **Integration Sequences**: API callouts, event-driven flows
- **System Landscapes**: High-level architecture, component diagrams
- **Role Hierarchies**: User hierarchies, profile/permission structures
- **Agentforce Flows**: Agent -> Topic -> Action flows
- **Dual Output**: Mermaid + ASCII fallback for every diagram
- **Org Discovery**: Query real metadata for accurate ERD diagrams

---

## Supported Diagram Types

| Type                  | Mermaid Syntax    | Use Case                                           |
| --------------------- | ----------------- | -------------------------------------------------- |
| OAuth Flows           | `sequenceDiagram` | Authorization Code, JWT Bearer, PKCE, Device Flow  |
| Data Models           | `flowchart LR`    | Object relationships with color coding (preferred) |
| Integration Sequences | `sequenceDiagram` | API callouts, event-driven flows                   |
| System Landscapes     | `flowchart`       | High-level architecture, component diagrams        |
| Role Hierarchies      | `flowchart`       | User hierarchies, profile/permission structures    |
| Agentforce Flows      | `flowchart`       | Agent -> Topic -> Action flows                     |

---

## Action Workflow

### Phase 1: Initialize & Gather Requirements

If the diagram requires org metadata (ERDs, permission hierarchies), call `org_init()` first.

**Ask the user** to gather:

- Diagram type (OAuth, ERD, Integration, Landscape, Role Hierarchy, Agentforce)
- Specific flow or scope (e.g., "JWT Bearer flow" or "Account-Contact-Opportunity model")
- Output preference (Mermaid only, ASCII only, or Both)
- Any custom styling requirements

### Phase 2: Template Selection

Select the appropriate template from `assets/`:

| Diagram Type              | Template File                      |
| ------------------------- | ---------------------------------- |
| Authorization Code Flow   | `oauth/authorization-code.md`      |
| Authorization Code + PKCE | `oauth/authorization-code-pkce.md` |
| JWT Bearer Flow           | `oauth/jwt-bearer.md`              |
| Client Credentials Flow   | `oauth/client-credentials.md`      |
| Device Authorization Flow | `oauth/device-authorization.md`    |
| Refresh Token Flow        | `oauth/refresh-token.md`           |
| Data Model (ERD)          | `datamodel/salesforce-erd.md`      |
| Sales Cloud ERD           | `datamodel/sales-cloud-erd.md`     |
| Service Cloud ERD         | `datamodel/service-cloud-erd.md`   |
| Integration Sequence      | `integration/api-sequence.md`      |
| System Landscape          | `architecture/system-landscape.md` |
| Role Hierarchy            | `role-hierarchy/user-hierarchy.md` |
| Agentforce Flow           | `agentforce/agent-flow.md`         |

### Phase 3: Data Collection

**For OAuth Diagrams**:

- Use standard actors (Browser, Client App, Salesforce)
- Include all protocol steps with numbered sequence

**For ERD/Data Model Diagrams**:

1. If org connected, query object metadata for accurate relationships:

```
sobject_describe(
  sObject="Account",
  sf_user="<sf_user>"
)
```

2. For record counts (LDV indicators):

```
soql_query(
  sObject="Account",
  fields=["COUNT(Id)"],
  sf_user="<sf_user>"
)
```

> **whereClause caveat**: Never pass an empty string `""` for `whereClause` — it generates malformed SQL (`WHERE ""`). Either omit `whereClause` entirely or use `"Id != null"` to select all records.

3. Identify relationships (Lookup vs Master-Detail)
4. Determine object types (Standard, Custom, External)
5. Generate `flowchart LR` with color coding

**For Integration Diagrams**:

- Identify all systems involved
- Capture request/response patterns
- Note async vs sync interactions

### Phase 4: Diagram Generation

**Generate Mermaid code**:

1. Apply color scheme (see Styling Guide below)
2. Add annotations and notes where helpful
3. Include `autonumber` for sequence diagrams
4. For data models: Use `flowchart LR` with object-type color coding
5. Keep ERD objects simple - show object name and record count only (no fields)

**Generate ASCII fallback**:

1. Use box-drawing characters: `--- | +`
2. Use arrows: `-->` `<--` `---`
3. Keep width under 80 characters when possible

**Score the diagram** against the 80-point rubric.

### Phase 5: Output & Documentation

**Delivery Format**:

````markdown
## [Diagram Title]

### Mermaid Diagram

```mermaid
[Generated Mermaid code]
```

### ASCII Fallback

```
[Generated ASCII diagram]
```

### Key Points

- [Important note 1]
- [Important note 2]

### Diagram Score

[Validation results]
````

---

## Data Model Notation

### Preferred Format: `flowchart LR`

Use `flowchart LR` (left-to-right) for data model diagrams. This format supports:

- Individual node color coding by object type
- Thick arrows (`==>`) for Master-Detail relationships
- Left-to-right flow for readability

### Object Type Color Coding

| Object Type              | Color    | Fill      | Stroke    |
| ------------------------ | -------- | --------- | --------- |
| Standard Objects         | Sky Blue | `#bae6fd` | `#0369a1` |
| Custom Objects (`__c`)   | Orange   | `#fed7aa` | `#c2410c` |
| External Objects (`__x`) | Green    | `#a7f3d0` | `#047857` |

### Relationship Arrows

```
-->   Lookup (LK) - optional parent, no cascade delete
==>   Master-Detail (MD) - required parent, cascade delete
-.->  Conversion/special relationship
```

### Object Node Format

```
ObjectName["ObjectName<br/>(record count)"]
```

Example: `Account["Account<br/>(317)"]`

### LDV (Large Data Volume) Indicators

Objects with >2M records display: `LDV[~4M]`

### OWD (Org-Wide Defaults)

Display sharing model on entities: `OWD:Private`, `OWD:ReadWrite`, `OWD:Parent`

---

## Data Model Templates

| Template                 | Objects                                                | Asset Path                              |
| ------------------------ | ------------------------------------------------------ | --------------------------------------- |
| **Core**                 | Account, Contact, Opportunity, Case                    | `datamodel/salesforce-erd.md`           |
| **Sales Cloud**          | Account, Contact, Lead, Opportunity, Product, Campaign | `datamodel/sales-cloud-erd.md`          |
| **Service Cloud**        | Case, Entitlement, Knowledge, ServiceContract          | `datamodel/service-cloud-erd.md`        |
| **Campaigns**            | Campaign, CampaignMember, CampaignInfluence            | `datamodel/campaigns-erd.md`            |
| **Territory Management** | Territory2, Territory2Model, UserTerritory2Association | `datamodel/territory-management-erd.md` |
| **Party Model**          | AccountContactRelation, ContactContactRelation         | `datamodel/party-model-erd.md`          |
| **Quote & Order**        | Quote, QuoteLineItem, Order, OrderItem                 | `datamodel/quote-order-erd.md`          |
| **Forecasting**          | ForecastingItem, ForecastingQuota, OpportunitySplit    | `datamodel/forecasting-erd.md`          |
| **Consent (GDPR)**       | Individual, ContactPointEmail, DataUsePurpose          | `datamodel/consent-erd.md`              |
| **Files**                | ContentDocument, ContentVersion, ContentDocumentLink   | `datamodel/files-erd.md`                |
| **Scheduler**            | ServiceAppointment, ServiceResource, ServiceTerritory  | `datamodel/scheduler-erd.md`            |
| **Field Service**        | WorkOrder, ServiceAppointment, TimeSheet               | `datamodel/fsl-erd.md`                  |
| **B2B Commerce**         | WebStore, WebCart, BuyerGroup, BuyerAccount            | `datamodel/b2b-commerce-erd.md`         |
| **Revenue Cloud**        | ProductCatalog, ProductSellingModel, PriceAdjustment   | `datamodel/revenue-cloud-erd.md`        |

---

## OAuth Flow Quick Reference

| Flow                     | Use Case                     | Key Detail                       | Template                           |
| ------------------------ | ---------------------------- | -------------------------------- | ---------------------------------- |
| **Authorization Code**   | Web apps with backend        | User -> Browser -> App -> SF     | `oauth/authorization-code.md`      |
| **Auth Code + PKCE**     | Mobile, SPAs, public clients | code_verifier + SHA256 challenge | `oauth/authorization-code-pkce.md` |
| **JWT Bearer**           | Server-to-server, CI/CD      | Sign JWT with private key        | `oauth/jwt-bearer.md`              |
| **Client Credentials**   | Service accounts, background | No user context                  | `oauth/client-credentials.md`      |
| **Device Authorization** | CLI, IoT, Smart TVs          | Poll for token after user auth   | `oauth/device-authorization.md`    |
| **Refresh Token**        | Extend access                | Reuse existing tokens            | `oauth/refresh-token.md`           |

---

## Mermaid Styling Guide

Use Tailwind 200-level pastel fills with dark strokes:

```
%%{init: {"flowchart": {"nodeSpacing": 80, "rankSpacing": 70}} }%%
style A fill:#fbcfe8,stroke:#be185d,color:#1f2937
```

**Common Color Palette**:

| Purpose                 | Fill      | Stroke    |
| ----------------------- | --------- | --------- |
| Standard Object (Blue)  | `#bae6fd` | `#0369a1` |
| Custom Object (Orange)  | `#fed7aa` | `#c2410c` |
| External Object (Green) | `#a7f3d0` | `#047857` |
| Salesforce Cloud        | `#ecfeff` | `#0e7490` |
| External System         | `#ecfdf5` | `#047857` |
| Process/Action          | `#c7d2fe` | `#4338ca` |
| Error/Warning           | `#fecaca` | `#b91c1c` |

---

## Scoring (80 Points)

```
Score: XX/80 - Rating
- Accuracy:       XX/20  (Correct actors, flow steps, relationships)
- Clarity:        XX/20  (Easy to read, proper labeling)
- Completeness:   XX/15  (All relevant steps/entities included)
- Styling:        XX/15  (Color scheme, theming, annotations)
- Best Practices: XX/10  (Proper notation, conventions)
```

**Thresholds**: 72-80 Excellent | 60-71 Very Good | 48-59 Good | 35-47 Needs Work | <35 Critical Issues

---

## Best Practices

### Sequence Diagrams

- Use `autonumber` for OAuth flows (step tracking)
- Use `->>` for requests, `-->>` for responses
- Use `activate`/`deactivate` for long-running processes
- Group related actors with `box` blocks
- Add `Note over` for protocol details

### Data Model Diagrams

- Use `flowchart LR` format (left-to-right flow)
- Keep objects simple: name + record count only (no fields)
- Color code by object type: Blue=Standard, Orange=Custom, Green=External
- Use `-->` for Lookup, `==>` for Master-Detail relationships
- Add LDV indicator for objects >2M records
- Use API names, not labels

### Integration Diagrams

- Show error paths with `alt`/`else` blocks
- Include timeout handling for external calls
- Mark async calls with `-)` notation

### ASCII Diagrams

- Keep width <= 80 characters
- Use consistent box sizes
- Align arrows clearly
- Add step numbers for sequences

---

## Cross-Skill Integration

| From Skill     | To sf-diagram | When                                      |
| -------------- | ------------- | ----------------------------------------- |
| sf-metadata    | -> sf-diagram | Get real object/field definitions for ERD |
| sf-permissions | -> sf-diagram | Visualize permission hierarchy            |
| sf-flow        | -> sf-diagram | Document Flow logic as flowchart          |

| From sf-diagram | To Skill          | When                                        |
| --------------- | ----------------- | ------------------------------------------- |
| sf-diagram      | -> sf-metadata    | Need object structure for ERD               |
| sf-diagram      | -> sf-permissions | Need permission data for hierarchy diagrams |

---

## Salesforce MCP tools (for Org Discovery)

### Describe Object

**Tool**: `sobject_describe`
**Purpose**: Get object structure, fields, relationships for ERD generation

```
sobject_describe(
  sObject="Account",
  sf_user="<sf_user>"
)
```

### Query Record Counts

**Tool**: `soql_query`
**Purpose**: Get record counts for LDV indicators

```
soql_query(
  sObject="Account",
  fields=["COUNT(Id)"],
  sf_user="<sf_user>"
)
```

### Query Metadata

**Tool**: `tooling_api_query`
**Purpose**: Query custom objects and relationships

```
tooling_api_query(
  sObject="CustomObject",
  fields=["DeveloperName", "Label"],
  sf_user="<sf_user>"
)
```

---

## Removed Capabilities

The following developer-focused features are **NOT needed** in this MCP-based version:

- `scripts/query-org-metadata.py` (Python CLI) - Use MCP tools instead
- `scripts/mermaid_preview.py` (localhost preview) - Not needed in sandboxed environments
- sf CLI metadata commands - Use `sobject_describe` / `tooling_api_query` instead

---

## Dependencies

- **Salesforce MCP server** (optional): For org metadata discovery in ERD diagrams
  - Tools: sobject_describe, soql_query, tooling_api_query
  - Diagrams can also be created from user-provided specifications without org connection

---

## Notes

- **Mermaid Rendering**: Works in GitHub, VS Code, Notion, Confluence, and most modern tools
- **ASCII Purpose**: Terminal compatibility, documentation that needs plain text
- **Color Accessibility**: Palette designed for color-blind accessibility
- **Template Customization**: Templates are starting points; customize per requirements
- **No Org Required**: OAuth, integration, and landscape diagrams don't need an org connection

---

## License

MIT License - See LICENSE file for details.
