# Bulk Operations Guide

When and how to use Salesforce Bulk API operations.

## Decision Matrix

| Record Count | Recommended API | Command                                        |
| ------------ | --------------- | ---------------------------------------------- |
| 1-10         | Single Record   | `sobject_dml(operation="insert", ...)`         |
| 11-2000      | Standard API    | `sobject_dml(operation="insert", ...)`         |
| 2000-10M     | Bulk API 2.0    | `sobject_dml(operation="insert", ...)` (batch) |
| 10M+         | Data Loader     | External tool                                  |

## Execution via Salesforce MCP (sf-data)

### Insert

```
sobject_dml(
  operation="insert",
  sobjectType="Account",
  records=[
    {"Name": "Acme Corp", "Industry": "Technology"},
    {"Name": "Globex Inc", "Industry": "Finance"}
  ]
)
```

### Update

```
sobject_dml(
  operation="update",
  sobjectType="Account",
  records=[
    {"Id": "001xx000003DGbYAAW", "Industry": "Healthcare"},
    {"Id": "001xx000003DGbZAAW", "Industry": "Finance"}
  ]
)
```

### Upsert (Insert or Update)

```
sobject_dml(
  operation="upsert",
  sobjectType="Account",
  externalIdField="External_Id__c",
  records=[
    {"External_Id__c": "EXT-001", "Name": "Acme Corp"},
    {"External_Id__c": "EXT-002", "Name": "Globex Inc"}
  ]
)
```

### Delete

```
sobject_dml(
  operation="delete",
  sobjectType="Account",
  records=[
    {"Id": "001xx000003DGbYAAW"},
    {"Id": "001xx000003DGbZAAW"}
  ]
)
```

### Export (Query)

```
soql_query(query="SELECT Id, Name FROM Account")
```

## CSV Format Requirements

- First row: Field API names
- UTF-8 encoding
- Comma delimiter (default)
- Max 100MB per file

## Bulk API Limits

| Limit                | Value      |
| -------------------- | ---------- |
| Batches per 24 hours | 10,000     |
| Records per 24 hours | 10,000,000 |
| Max file size        | 100 MB     |
| Max concurrent jobs  | 100        |

## Error Handling

The MCP `sobject_dml` tool returns results directly, including any per-record errors. No separate job status or result retrieval commands are needed.

## Best Practices

1. **Chunk large record sets** - Split into batches for large operations
2. **Handle partial failures** - Check per-record results from `sobject_dml`
3. **Test in sandbox** - Validate before production
