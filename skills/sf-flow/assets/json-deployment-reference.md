# JSON Deployment Reference for `metadata_create`

This reference covers how to construct Flow metadata JSON objects for deployment via the Salesforce MCP server's `metadata_create` and `metadata_update` tools. The XML templates in `assets/` show the correct structure — this document explains how to translate them to JSON and highlights JSON-specific rules.

## 1. XML-to-JSON Translation Rules

The XML templates in `assets/` are the structural source of truth. To translate for `metadata_create`:

| XML Pattern                                                             | JSON Equivalent                                            |
| ----------------------------------------------------------------------- | ---------------------------------------------------------- |
| `<stringValue>text</stringValue>`                                       | `{"stringValue": "text"}`                                  |
| `<booleanValue>true</booleanValue>`                                     | `{"booleanValue": true}`                                   |
| `<numberValue>100</numberValue>`                                        | `{"numberValue": 100}`                                     |
| `<elementReference>var_Name</elementReference>`                         | `{"elementReference": "var_Name"}`                         |
| `<connector><targetReference>X</targetReference></connector>`           | `"connector": {"targetReference": "X"}`                    |
| `<faultConnector><targetReference>X</targetReference></faultConnector>` | `"faultConnector": {"targetReference": "X"}`               |
| Repeated XML elements (e.g., multiple `<filters>`)                      | JSON array of objects                                      |
| XML element name (e.g., `<recordUpdates>`)                              | JSON key with array value (e.g., `"recordUpdates": [...]`) |

**Key difference**: XML uses nested element tags; JSON uses flat key-value pairs with typed value wrappers.

## 2. Property Placement Rules

These properties belong ONLY inside `start`, never at the top level:

| Property                                    | Values                                                                                    | When Required                             |
| ------------------------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------- |
| `triggerType`                               | `RecordAfterSave`, `RecordBeforeSave`, `RecordBeforeDelete`, `Scheduled`, `PlatformEvent` | All triggered flows                       |
| `recordTriggerType`                         | `Create`, `Update`, `CreateAndUpdate`, `Delete`                                           | Record-triggered flows                    |
| `object`                                    | SObject API name                                                                          | Record-triggered and platform event flows |
| `schedule`                                  | `{frequency, startDate, startTime}`                                                       | Scheduled flows                           |
| `filters` / `filterFormula` / `filterLogic` | Entry conditions                                                                          | Record-triggered flows (optional)         |

Top-level properties are: `fullName`, `apiVersion`, `label`, `description`, `processType`, `status`, `environments`, `interviewLabel`, `processMetadataValues`, `start`, and element arrays (`decisions`, `assignments`, `recordCreates`, etc.).

## 3. Start Element Patterns (JSON)

### Record-triggered (after save) — filterFormula (preferred for compound conditions)

```json
"start": {
  "locationX": 0, "locationY": 0,
  "object": "Case",
  "recordTriggerType": "Update",
  "triggerType": "RecordAfterSave",
  "filterFormula": "AND({!$Record.Status} = 'Closed', NOT({!$Record.Already_Processed__c}))",
  "connector": {"targetReference": "First_Element"}
}
```

### Record-triggered (after save) — filters array (simple conditions)

```json
"start": {
  "locationX": 0, "locationY": 0,
  "object": "Case",
  "recordTriggerType": "Update",
  "triggerType": "RecordAfterSave",
  "filterLogic": "and",
  "filters": [
    {"field": "Status", "operator": "EqualTo", "value": {"stringValue": "Closed"}}
  ],
  "connector": {"targetReference": "First_Element"}
}
```

### Record-triggered (before save)

```json
"start": {
  "locationX": 0, "locationY": 0,
  "object": "Lead",
  "recordTriggerType": "Create",
  "triggerType": "RecordBeforeSave",
  "connector": {"targetReference": "Set_Defaults"}
}
```

### Scheduled flow

```json
"start": {
  "locationX": 0, "locationY": 0,
  "triggerType": "Scheduled",
  "schedule": {
    "frequency": "Daily",
    "startDate": "2025-01-01",
    "startTime": "02:00:00.000Z"
  },
  "connector": {"targetReference": "Get_Records"}
}
```

### Platform event

```json
"start": {
  "locationX": 0, "locationY": 0,
  "object": "Order_Event__e",
  "triggerType": "PlatformEvent",
  "connector": {"targetReference": "Process_Event"}
}
```

### Autolaunched (no trigger)

```json
"start": {
  "locationX": 0, "locationY": 0,
  "connector": {"targetReference": "First_Element"}
}
```

### Screen flow

```json
"start": {
  "locationX": 0, "locationY": 0,
  "connector": {"targetReference": "First_Screen"}
}
```

## 4. Entry Condition Patterns

Use `filterFormula` for compound or negated conditions:

```json
"filterFormula": "AND({!$Record.Amount} > 100000, NOT({!$Record.High_Value_Notified__c}))"
"filterFormula": "OR({!$Record.Status} = 'Closed', ISBLANK({!$Record.OwnerId}))"
"filterFormula": "ISCHANGED({!$Record.Stage__c})"
```

Use `filters` array for simple field comparisons:

```json
"filterLogic": "and",
"filters": [
  {"field": "Status", "operator": "EqualTo", "value": {"stringValue": "Closed"}},
  {"field": "Priority", "operator": "EqualTo", "value": {"stringValue": "High"}}
]
```

Custom filter logic with numbered references:

```json
"filterLogic": "(1 OR 2) AND 3",
"filters": [
  {"field": "Status", "operator": "EqualTo", "value": {"stringValue": "Open"}},
  {"field": "Status", "operator": "EqualTo", "value": {"stringValue": "Working"}},
  {"field": "LeadSource", "operator": "EqualTo", "value": {"stringValue": "Web"}}
]
```

**Filter operators**: `EqualTo`, `NotEqualTo`, `GreaterThan`, `GreaterThanOrEqual`, `LessThan`, `LessThanOrEqualTo`, `Contains`, `StartsWith`, `EndsWith`, `IsNull`, `IsChanged` (record-triggered only).

## 5. Value Reference Patterns

| Pattern            | JSON                                               | When to Use                 |
| ------------------ | -------------------------------------------------- | --------------------------- |
| Literal string     | `{"stringValue": "text"}`                          | Fixed text, picklist values |
| Literal boolean    | `{"booleanValue": true}`                           | Checkbox values, flags      |
| Literal number     | `{"numberValue": 100}`                             | Numeric thresholds, counts  |
| Variable reference | `{"elementReference": "var_Name"}`                 | Flow variables              |
| Record field       | `{"elementReference": "$Record.FieldName"}`        | Trigger record fields       |
| Prior value        | `{"elementReference": "$Record__Prior.FieldName"}` | Update triggers only        |
| Fault message      | `{"elementReference": "$Flow.FaultMessage"}`       | Inside fault paths          |
| Loop current item  | `{"elementReference": "Loop_Name"}`                | Inside loop body            |

**Merge fields in strings**: `stringValue` supports `{!variable}` syntax for interpolation. Use this for email subjects, bodies, and labels instead of creating formula variables:

```json
{"stringValue": "Hello {!$Record.Name}, your case {!$Record.CaseNumber} has been updated."}
{"stringValue": "Total: {!var_TotalAmount} records processed"}
```

## 6. Element JSON Patterns

Each element type corresponds to a top-level array in the flow JSON. See the XML templates in `assets/` and `assets/elements/` for full structural patterns. Below are compact JSON examples for each type.

### Decision

```json
"decisions": [{
  "name": "Check_Status",
  "label": "Check Status",
  "locationX": 0, "locationY": 0,
  "defaultConnectorLabel": "Default Outcome",
  "rules": [{
    "name": "Is_Active",
    "conditionLogic": "and",
    "conditions": [{
      "leftValueReference": "$Record.Status",
      "operator": "EqualTo",
      "rightValue": {"stringValue": "Active"}
    }],
    "connector": {"targetReference": "Next_Element"},
    "label": "Active"
  }]
}]
```

### Record Create (with fault path)

```json
"recordCreates": [{
  "name": "Create_Task",
  "label": "Create Task",
  "locationX": 0, "locationY": 0,
  "object": "Task",
  "inputAssignments": [
    {"field": "Subject", "value": {"stringValue": "Follow up"}},
    {"field": "WhoId", "value": {"elementReference": "$Record.Id"}}
  ],
  "connector": {"targetReference": "Next_Element"},
  "faultConnector": {"targetReference": "Handle_Error"}
}]
```

### Record Update (with fault path)

```json
"recordUpdates": [{
  "name": "Update_Record",
  "label": "Update Record",
  "locationX": 0, "locationY": 0,
  "object": "Opportunity",
  "filters": [
    {"field": "Id", "operator": "EqualTo", "value": {"elementReference": "$Record.Id"}}
  ],
  "inputAssignments": [
    {"field": "High_Value_Notified__c", "value": {"booleanValue": true}}
  ],
  "connector": {"targetReference": "Next_Element"},
  "faultConnector": {"targetReference": "Handle_Error"}
}]
```

### Record Lookup (Get Records)

See `assets/elements/get-records-pattern.xml` for 5 comprehensive patterns. Compact JSON:

```json
"recordLookups": [{
  "name": "Get_Account",
  "label": "Get Account",
  "locationX": 0, "locationY": 0,
  "object": "Account",
  "filterLogic": "and",
  "filters": [
    {"field": "Id", "operator": "EqualTo", "value": {"elementReference": "var_AccountId"}}
  ],
  "getFirstRecordOnly": true,
  "outputReference": "rec_Account",
  "queriedFields": ["Id", "Name", "Industry"],
  "assignNullValuesIfNoRecordsFound": true,
  "connector": {"targetReference": "Decision_Record_Found"}
}]
```

### Action Call (e.g., send email)

```json
"actionCalls": [{
  "name": "Send_Email",
  "label": "Send Email",
  "locationX": 0, "locationY": 0,
  "actionName": "emailSimple",
  "actionType": "emailSimple",
  "flowTransactionModel": "CurrentTransaction",
  "inputParameters": [
    {"name": "emailAddresses", "value": {"stringValue": "admin@example.com"}},
    {"name": "emailSubject", "value": {"stringValue": "Alert: {!$Record.Name}"}},
    {"name": "emailBody", "value": {"stringValue": "Details here"}}
  ],
  "connector": {"targetReference": "Next_Element"},
  "faultConnector": {"targetReference": "Handle_Error"}
}]
```

### Assignment

```json
"assignments": [{
  "name": "Set_Message",
  "label": "Set Message",
  "locationX": 0, "locationY": 0,
  "assignmentItems": [
    {"assignToReference": "var_Message", "operator": "Assign", "value": {"stringValue": "Done"}}
  ],
  "connector": {"targetReference": "Next_Element"}
}]
```

### Variable

```json
"variables": [{
  "name": "var_AccountName",
  "dataType": "String",
  "isCollection": false,
  "isInput": true,
  "isOutput": false
}]
```

### Loop

See `assets/elements/loop-pattern.xml` for complete pattern.

```json
"loops": [{
  "name": "Loop_Records",
  "label": "Loop Records",
  "locationX": 0, "locationY": 0,
  "collectionReference": "col_Records",
  "iterationOrder": "Asc",
  "nextValueConnector": {"targetReference": "Process_Item"},
  "noMoreValuesConnector": {"targetReference": "After_Loop"}
}]
```

### Record Delete

See `assets/elements/record-delete-pattern.xml` for filter-based and reference-based patterns.

```json
"recordDeletes": [{
  "name": "Delete_Old_Records",
  "label": "Delete Old Records",
  "locationX": 0, "locationY": 0,
  "inputReference": "col_RecordsToDelete",
  "connector": {"targetReference": "Next_Element"},
  "faultConnector": {"targetReference": "Handle_Error"}
}]
```
