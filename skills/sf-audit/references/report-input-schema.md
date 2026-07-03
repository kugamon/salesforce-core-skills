# Input Schema for generate_reports.py

The report generator reads JSON files from the `--input-dir` directory.
All files are optional — missing files produce empty sections.

## counts.json

Component inventory counts. Also carries org metadata used in report headers.

```json
{
  "org_name": "Acme Corp",
  "org_id": "00D000000000001AAA",
  "instance": "CS42",
  "apex_classes": 45,
  "apex_triggers": 8,
  "active_flows": 12,
  "process_builders": 3,
  "lwc_bundles": 15,
  "custom_objects": 22,
  "validation_rules": 30,
  "workflow_rules": 5,
  "formula_fields": 42,
  "approval_processes": 3,
  "permission_sets": 18,
  "permission_set_groups": 4,
  "profiles": 6,
  "active_users": 150
}
```

## apex_scores.json

Array of scored Apex classes.

```json
[
  {
    "name": "AccountService",
    "score": 120,
    "max_score": 150,
    "issues": ["Missing null checks", "No test class found"]
  }
]
```

## trigger_findings.json

Array of Apex triggers with qualitative findings (not scored).

```json
[
  {
    "name": "ContactTrigger",
    "object": "Contact",
    "events": "before insert, before update",
    "findings": [{ "severity": "HIGH", "message": "Logic inside trigger body" }]
  }
]
```

## flow_scores.json

Array of scored Flows.

```json
[
  {
    "name": "Account_Update_Flow",
    "process_type": "RecordTriggeredFlow",
    "score": 85,
    "max_score": 110,
    "issues": ["No fault path on DML element"]
  }
]
```

## process_builders.json

Array of Process Builder inventory items (not scored).

```json
[
  {
    "name": "Update_Account_Status",
    "object": "Account",
    "criteria_count": 5,
    "actions_summary": "2 field updates, 1 email alert",
    "migration_priority": "HIGH"
  }
]
```

## lwc_scores.json

Array of scored Lightning Web Components.

```json
[
  {
    "name": "accountDashboard",
    "score": 130,
    "max_score": 165,
    "issues": ["Missing error handling in wire adapter"]
  }
]
```

## permission_findings.json

Array of permission-related findings. Each item must have a `type` field
(`"profile"` or `"permission_set"`) for proper Excel sheet routing.

```json
[
  {
    "type": "permission_set",
    "name": "Full_Access_PS",
    "label": "Full Access",
    "assignments": 3,
    "severity": "CRITICAL",
    "message": "Non-admin Permission Set with ModifyAllData enabled"
  },
  {
    "type": "profile",
    "name": "Custom Sales Profile",
    "user_type": "Standard",
    "key_permissions": "ViewAllData",
    "severity": "HIGH",
    "message": "Custom Profile with ViewAllData"
  }
]
```

## metadata_scores.json

Array of scored custom objects.

```json
[
  {
    "name": "Project__c",
    "score": 90,
    "max_score": 120,
    "field_count": 25,
    "relationship_count": 3,
    "issues": ["Missing description on 5 custom fields"]
  }
]
```

## validation_rules.json

Array of validation rules with findings. Includes formula-body anti-pattern
findings when `ErrorConditionFormula` was retrieved.

```json
[
  {
    "name": "Require_Amount",
    "object": "Opportunity",
    "active": true,
    "findings": [
      { "severity": "MEDIUM", "message": "No bypass mechanism" },
      { "severity": "HIGH", "message": "Formula contains hardcoded Record ID: 0015000000XyZaB" }
    ]
  }
]
```

## formula_fields.json

Array of formula fields with anti-pattern findings.

```json
[
  {
    "name": "Region_Label__c",
    "object": "Account",
    "data_type": "Text",
    "formula_length": 1240,
    "findings": [
      { "severity": "HIGH", "message": "Formula contains hardcoded Record ID: 0125000000AbCdE" },
      {
        "severity": "MEDIUM",
        "message": "Formula contains hardcoded Profile name: \"System Administrator\""
      }
    ]
  },
  {
    "name": "Tier__c",
    "object": "Account",
    "data_type": "Text",
    "formula_length": 320,
    "findings": []
  }
]
```

## workflow_rules.json

Array of workflow rule inventory items. Includes formula-body anti-pattern
findings when criteria/field-update formulas were retrieved via `metadata_read`.

```json
[
  {
    "name": "Set_Default_Status",
    "object": "Case",
    "action_types": "Field Update",
    "migration_priority": "HIGH",
    "findings": [
      {
        "severity": "HIGH",
        "message": "Criteria formula contains hardcoded Record ID: 00Q5000000AbCdE"
      }
    ]
  }
]
```

## unused_fields.json

Array of custom fields flagged as unused, empty, or unreferenced.

```json
[
  {
    "object": "Project__c",
    "field": "Legacy_Status__c",
    "data_type": "Picklist",
    "has_data": false,
    "referenced_in": [],
    "category": "Unused",
    "severity": "HIGH"
  },
  {
    "object": "Account",
    "field": "Old_Region__c",
    "data_type": "Text",
    "has_data": false,
    "referenced_in": ["AccountService.cls", "Account_Update_Flow"],
    "category": "Empty",
    "severity": "MEDIUM"
  },
  {
    "object": "Contact",
    "field": "Internal_Code__c",
    "data_type": "Text",
    "has_data": true,
    "referenced_in": [],
    "category": "Unreferenced",
    "severity": "MEDIUM"
  }
]
```

Categories:

| Category       | Condition                  | Severity |
| -------------- | -------------------------- | -------- |
| `Unused`       | No data AND no references  | HIGH     |
| `Empty`        | No data but has references | MEDIUM   |
| `Unreferenced` | Has data but no references | MEDIUM   |

`has_data` is a tri-state value: `true` (records contain data), `false`
(no records with data), or `null` (population check was skipped, e.g. in
`sfdx-repo` mode). Reports render `null` as "Unknown".

Fields in the `Active` category (has data AND has references) are **not**
included in this file.

## unused_objects.json

Array of custom objects flagged as unused, empty, or unreferenced.

```json
[
  {
    "object": "Legacy_Request__c",
    "record_count": 0,
    "referenced_in": [],
    "category": "Unused",
    "severity": "HIGH"
  },
  {
    "object": "Staging_Record__c",
    "record_count": 0,
    "referenced_in": ["StagingBatch.cls"],
    "category": "Empty",
    "severity": "MEDIUM"
  },
  {
    "object": "Archive__c",
    "record_count": 1500,
    "referenced_in": [],
    "category": "Unreferenced",
    "severity": "MEDIUM"
  }
]
```

Categories follow the same rules as `unused_fields.json` but use
`record_count` instead of `has_data`.

## other_rules_findings.json

Array of findings from approval processes, escalation rules, assignment rules,
and auto-response rules.

```json
[
  {
    "type": "ApprovalProcess",
    "name": "Discount_Approval",
    "object": "Opportunity",
    "findings": [
      {
        "severity": "HIGH",
        "message": "Entry criteria contains hardcoded Record ID: 0055000000XyZaB"
      }
    ]
  },
  {
    "type": "EscalationRule",
    "name": "Case_Escalation",
    "object": "Case",
    "findings": [
      {
        "severity": "MEDIUM",
        "message": "Rule entry criteria contains hardcoded Profile name: \"Support Agent\""
      }
    ]
  }
]
```

## reports_dashboards.json

Reports and Dashboards inventory with stale detection.

```json
{
  "reports": [
    {
      "name": "Pipeline by Stage",
      "folder": "Sales Reports",
      "format": "MATRIX",
      "last_run_date": "2025-11-01",
      "created_date": "2024-03-15",
      "is_stale": false
    }
  ],
  "dashboards": [
    {
      "name": "Executive KPIs",
      "folder": "Leadership",
      "last_viewed_date": "2026-01-10",
      "created_date": "2024-06-01",
      "is_stale": false
    }
  ],
  "findings": [{ "severity": "MEDIUM", "message": "12 reports have never been run" }]
}
```

## integrations.json

Array of integration-related metadata items with findings.

```json
[
  {
    "type": "ConnectedApp",
    "name": "Slack Integration",
    "endpoint": null,
    "findings": [{ "severity": "LOW", "message": "No description provided" }]
  },
  {
    "type": "NamedCredential",
    "name": "ERP_Endpoint",
    "endpoint": "https://erp.example.com/api",
    "findings": []
  }
]
```

## test_coverage.json

Apex test coverage data — org-wide and per-class.

```json
{
  "org_wide_pct": 82.5,
  "classes": [
    {
      "name": "AccountService",
      "lines_covered": 120,
      "lines_uncovered": 30,
      "coverage_pct": 80.0
    }
  ],
  "findings": [{ "severity": "HIGH", "message": "3 classes have 0% test coverage" }]
}
```

## team_evaluation.json

User distribution, activity, and role analysis.

```json
{
  "active_users": 150,
  "users": [
    {
      "name": "Jane Smith",
      "username": "jane@acme.com",
      "profile": "System Administrator",
      "role": "CEO",
      "last_login": "2026-04-01",
      "days_since_login": 6,
      "permission_set_count": 4,
      "login_count_180d": 95
    }
  ],
  "profile_distribution": [{ "profile": "System Administrator", "user_count": 8 }],
  "findings": [{ "severity": "HIGH", "message": "12 users inactive for > 90 days" }]
}
```

## change_history.json

Setup audit trail and deployment history.

```json
{
  "audit_trail": [
    {
      "date": "2026-04-01T14:30:00Z",
      "user": "Admin User",
      "action": "Changed field-level security",
      "section": "Manage Users",
      "detail": "Changed field Account.Revenue__c"
    }
  ],
  "change_distribution": [{ "section": "Manage Users", "count": 245 }],
  "top_changers": [{ "user": "Admin User", "change_count": 312 }],
  "deployments": [
    {
      "id": "0Af000000001234",
      "status": "Succeeded",
      "date": "2026-03-28T10:00:00Z",
      "user": "Release Manager",
      "components_deployed": 45,
      "component_errors": 0
    }
  ],
  "deployment_success_rate": 85.0,
  "findings": [{ "severity": "HIGH", "message": "Deployment failure rate is 15%" }]
}
```

## licensing.json

Licence type inventory with utilisation analysis.

```json
{
  "user_licenses": [
    {
      "name": "Salesforce",
      "total": 100,
      "used": 75,
      "available": 25,
      "utilization_pct": 75.0
    }
  ],
  "permission_set_licenses": [
    {
      "name": "SalesforceCPQ_CPQStandardPerm",
      "label": "Salesforce CPQ License",
      "total": 50,
      "used": 5,
      "available": 45,
      "utilization_pct": 10.0
    }
  ],
  "package_licenses": [
    {
      "namespace": "SBQQ",
      "allowed": 50,
      "used": 5,
      "expiration_date": "2026-12-31",
      "status": "Active"
    }
  ],
  "findings": [{ "severity": "HIGH", "message": "SalesforceCPQ_CPQStandardPerm: 10% utilisation" }]
}
```

## data_quality.json

Data completeness spot-checks on key objects.

```json
{
  "objects": [
    {
      "name": "Account",
      "record_count": 50000,
      "field_completeness": [
        { "field": "Industry", "null_count": 12000, "null_pct": 24.0 },
        { "field": "BillingCity", "null_count": 8500, "null_pct": 17.0 }
      ]
    }
  ],
  "findings": [{ "severity": "HIGH", "message": "Account.Industry is null for 24% of records" }]
}
```
