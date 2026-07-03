# CRUD Workflow Example

Complete end-to-end example of data operations using sf-data skill.

## Scenario

Create a Deal Desk workflow test environment with:

- Accounts with varying revenue tiers
- Contacts as decision makers
- Opportunities at different stages

## Phase 1: Discovery (sf-metadata)

```
Skill(skill="sf-metadata")
Request: "Describe object Account in org dev - show required fields and picklist values"
```

**Response shows:**

- Required: Name
- Picklists: Industry, Type, Rating

## Phase 2: Create Records (sf-data)

### Salesforce MCP - Single Record

```
sobject_dml(
  operation="insert",
  sobjectType="Account",
  records=[{Name: "Enterprise Corp", Industry: "Technology", AnnualRevenue: 5000000}],
  orgAlias="dev"
)
```

**Output:**

```json
{
  "status": 0,
  "result": {
    "id": "001XXXXXXXXXXXX",
    "success": true
  }
}
```

### Salesforce MCP - Query Created Record

```
soql_query(
  query="SELECT Id, Name, Industry, AnnualRevenue FROM Account WHERE Name = 'Enterprise Corp'",
  orgAlias="dev"
)
```

## Phase 3: Update Records

### Update Single Record

```
sobject_dml(
  operation="update",
  sobjectType="Account",
  records=[{Id: "001XXXXXXXXXXXX", Rating: "Hot", Type: "Customer - Direct"}],
  orgAlias="dev"
)
```

### Verify Update

```
soql_query(
  query="SELECT Id, Name, Rating, Type FROM Account WHERE Id = '001XXXXXXXXXXXX'",
  orgAlias="dev"
)
```

## Phase 4: Create Related Records

### Create Contact for Account

```
sobject_dml(
  operation="insert",
  sobjectType="Contact",
  records=[{FirstName: "John", LastName: "Smith", AccountId: "001XXXXXXXXXXXX", Title: "CTO"}],
  orgAlias="dev"
)
```

### Create Opportunity

```
sobject_dml(
  operation="insert",
  sobjectType="Opportunity",
  records=[{Name: "Enterprise Deal", AccountId: "001XXXXXXXXXXXX", StageName: "Prospecting", CloseDate: "2025-03-31", Amount: 250000}],
  orgAlias="dev"
)
```

## Phase 5: Query Relationships

### Parent-to-Child (Subquery)

```
soql_query(
  query="SELECT Id, Name, (SELECT Id, Name, Title FROM Contacts), (SELECT Id, Name, Amount, StageName FROM Opportunities) FROM Account WHERE Name = 'Enterprise Corp'",
  orgAlias="dev"
)
```

### Child-to-Parent (Dot Notation)

```
soql_query(
  query="SELECT Id, Name, Account.Name, Account.Industry FROM Contact WHERE Account.Name = 'Enterprise Corp'",
  orgAlias="dev"
)
```

## Phase 6: Delete Records

### Delete in Correct Order

Children first, then parents:

```
# Delete Opportunities
sobject_dml(
  operation="delete",
  sobjectType="Opportunity",
  records=[{Id: "006XXXXXXXXXXXX"}],
  orgAlias="dev"
)

# Delete Contacts
sobject_dml(
  operation="delete",
  sobjectType="Contact",
  records=[{Id: "003XXXXXXXXXXXX"}],
  orgAlias="dev"
)

# Delete Account
sobject_dml(
  operation="delete",
  sobjectType="Account",
  records=[{Id: "001XXXXXXXXXXXX"}],
  orgAlias="dev"
)
```

## Anonymous Apex Alternative

For complex operations, use Anonymous Apex:

```apex
// Create complete hierarchy in one transaction
Account acc = new Account(
    Name = 'Enterprise Corp',
    Industry = 'Technology',
    AnnualRevenue = 5000000
);
insert acc;

Contact con = new Contact(
    FirstName = 'John',
    LastName = 'Smith',
    AccountId = acc.Id,
    Title = 'CTO'
);
insert con;

Opportunity opp = new Opportunity(
    Name = 'Enterprise Deal',
    AccountId = acc.Id,
    ContactId = con.Id,
    StageName = 'Prospecting',
    CloseDate = Date.today().addDays(90),
    Amount = 250000
);
insert opp;

System.debug('Created hierarchy: Account=' + acc.Id + ', Contact=' + con.Id + ', Opp=' + opp.Id);
```

Execute:

```
# Execute via Apex execution in Salesforce Setup or the MCP tooling_api_dml tool
# No direct MCP equivalent for anonymous Apex execution
```

## Validation Score

```
Score: 125/130 ⭐⭐⭐⭐⭐ Excellent
├─ Query Efficiency: 25/25 (indexed fields, no N+1)
├─ Bulk Safety: 23/25 (single records OK for demo)
├─ Data Integrity: 20/20 (all required fields)
├─ Security & FLS: 20/20 (no PII exposed)
├─ Test Patterns: 12/15 (single record demo)
├─ Cleanup & Isolation: 15/15 (proper delete order)
└─ Documentation: 10/10 (fully documented)
```
