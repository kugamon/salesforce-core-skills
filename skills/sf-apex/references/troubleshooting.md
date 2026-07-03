# Apex Troubleshooting Guide

Comprehensive guide to debugging Apex code, LSP validation, dependency management, and common deployment issues.

---

## Table of Contents

1. [Cross-Skill Dependency Checklist](#cross-skill-dependency-checklist)
2. [Common Deployment Errors](#common-deployment-errors)
3. [Debug Logs and Monitoring](#debug-logs-and-monitoring)
4. [Governor Limit Debugging](#governor-limit-debugging)
5. [Test Failures](#test-failures)

---

## Cross-Skill Dependency Checklist

**Before deploying Apex code, verify these prerequisites:**

| Prerequisite              | Check Command                                                 | Required For                |
| ------------------------- | ------------------------------------------------------------- | --------------------------- |
| **TAF Package**           | `tooling_api_query(sobjectType="InstalledSubscriberPackage")` | TAF trigger pattern         |
| **Custom Fields**         | `sobject_describe(sobjectType="Lead")`                        | Field references in code    |
| **Permission Sets**       | `soql_query(query="SELECT Id, Name FROM PermissionSet")`      | FLS for custom fields       |
| **Trigger_Action\_\_mdt** | Check Setup → Custom Metadata Types                           | TAF trigger execution       |
| **Named Credentials**     | Check Setup → Named Credentials                               | External callouts           |
| **Custom Settings**       | Check Setup → Custom Settings                                 | Bypass flags, configuration |

---

### Common Deployment Order

```
1. sf-metadata: Create custom fields
   └─> metadata_create(type="CustomField", fullName="Lead.Score__c", metadata={...})

2. sf-metadata: Create Permission Sets
   └─> Grant FLS on custom fields

3. sf-deploy: Deploy fields + Permission Sets
   └─> metadata_create(type="CustomField", ...)

4. sf-apex: Deploy Apex classes/triggers
   └─> tooling_api_dml(operation="insert", sObject="ApexClass", record={"Name":"MyClass","Body":"...","Status":"Active","ApiVersion":"65.0"})

5. sf-data: Create test data
   └─> sobject_dml(operation="insert", sobjectType="Account", records=[{Name: "Test"}])
```

---

### Verifying Prerequisites

**Check TAF Package:**

```
tooling_api_query(sobjectType="InstalledSubscriberPackage")
```

**Expected Result:** Look for "Trigger Actions Framework" in the response.

**If not installed:**

```
# Package install: use metadata_create or Salesforce Setup
# Install package 04tKZ000000gUEFYA2 via Salesforce Setup → Installed Packages
```

---

**Check Custom Metadata Records:**

```
soql_query(query="SELECT DeveloperName, Object__c, Apex_Class_Name__c FROM Trigger_Action__mdt")
```

**Expected Output:**

```
DeveloperName          Object__c  Apex_Class_Name__c
─────────────────────────────────────────────────────
TA_Account_SetDefaults  Account    TA_Account_SetDefaults
TA_Lead_CalculateScore  Lead       TA_Lead_CalculateScore
```

**If missing, create via sf-metadata skill.**

---

## Common Deployment Errors

### Error: "Field does not exist"

**Cause**: Apex references a custom field that doesn't exist in target org.

**Example:**

```
Error: Field Account.Custom_Field__c does not exist
```

**Fix:**

1. Verify field exists:

   ```
   sobject_describe(sobjectType="Account")
   ```

2. Deploy field first:

   ```
   metadata_create(type="CustomField", fullName="Account.Custom_Field__c", metadata={...})
   ```

3. Then deploy Apex

---

### Error: "Invalid type: TriggerAction"

**Cause**: TAF package not installed in target org.

**Example:**

```
Error: Invalid type: TriggerAction.BeforeInsert
```

**Fix:**

```
# Package install: use metadata_create or Salesforce Setup
# Install package 04tKZ000000gUEFYA2 via Salesforce Setup → Installed Packages

# Verify
tooling_api_query(sobjectType="InstalledSubscriberPackage")
```

---

### Error: "Insufficient access rights"

**Cause**: Deploy user lacks permissions.

**Example:**

```
Error: Insufficient access rights on object id
```

**Fix:**

1. Verify user has "Modify All Data" or is System Administrator
2. Or add specific permissions to user's profile via Salesforce Setup → Permission Set Assignments

---

### Error: "Test coverage less than 75%"

**Cause**: Production deployment requires 75% test coverage.

**Example:**

```
Error: Average test coverage across all Apex Classes and Triggers is 68%, at least 75% required
```

**Fix:**

1. Identify uncovered classes:

   ```
   # Test execution: use sf-testing skill or Salesforce Setup
   ```

2. Add missing test classes

3. Ensure tests have assertions:
   ```apex
   Assert.areEqual(expected, actual, 'Message');
   ```

---

### Error: "FIELD_CUSTOM_VALIDATION_EXCEPTION"

**Cause**: Apex code violates validation rule.

**Example:**

```
Error: FIELD_CUSTOM_VALIDATION_EXCEPTION: Annual Revenue must be greater than 0
```

**Fix:**

1. Check validation rules:

   ```
   soql_query(query="SELECT ValidationName, ErrorDisplayField, ErrorMessage FROM ValidationRule WHERE EntityDefinition.QualifiedApiName = 'Account'")
   ```

2. Update Apex to satisfy validation logic:
   ```apex
   acc.AnnualRevenue = 1000000;  // Ensure > 0
   ```

---

## Debug Logs and Monitoring

### Enable Debug Logs

**Via Setup:**

1. Setup → Debug Logs
2. Click "New"
3. Select User
4. Set expiration (max 24 hours)
5. Set log levels:
   - Apex Code: `DEBUG`
   - Database: `INFO`
   - Workflow: `INFO`

**Via CLI:**

```
# Create trace flag
sobject_dml(operation="insert", sobjectType="TraceFlag", records=[{StartDate: "2025-01-01T00:00:00Z", EndDate: "2025-01-02T00:00:00Z", LogType: "USER_DEBUG", TracedEntityId: "<USER_ID>", DebugLevelId: "<DEBUG_LEVEL_ID>"}])

# Debug logs: use sf-debug skill or Salesforce Setup
```

---

### Reading Debug Logs

**Structure:**

```
HH:MM:SS.SSS|EXECUTION_STARTED
HH:MM:SS.SSS|CODE_UNIT_STARTED|AccountService
HH:MM:SS.SSS|USER_DEBUG|[3]|DEBUG|Processing account: Test
HH:MM:SS.SSS|SOQL_EXECUTE_BEGIN|[5]|SELECT Id FROM Account
HH:MM:SS.SSS|SOQL_EXECUTE_END|[5]|Rows:10
HH:MM:SS.SSS|DML_BEGIN|[8]|Op:Update|Type:Account|Rows:10
HH:MM:SS.SSS|DML_END|[8]
HH:MM:SS.SSS|LIMIT_USAGE_FOR_NS|(default)|SOQL:1/100|DML:1/150
HH:MM:SS.SSS|EXECUTION_FINISHED
```

**Key Events:**

- `USER_DEBUG`: Your `System.debug()` statements
- `SOQL_EXECUTE_*`: SOQL queries
- `DML_BEGIN/END`: DML operations
- `LIMIT_USAGE_FOR_NS`: Governor limit consumption

---

### Strategic Debug Statements

```apex
public static void processAccounts(List<Account> accounts) {
    System.debug(LoggingLevel.INFO, '=== START processAccounts ===');
    System.debug(LoggingLevel.INFO, 'Input size: ' + accounts.size());

    // Log limits BEFORE expensive operation
    System.debug('SOQL before: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());

    List<Contact> contacts = [SELECT Id, AccountId FROM Contact WHERE AccountId IN :accountIds];

    // Log limits AFTER
    System.debug('SOQL after: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
    System.debug('Contacts retrieved: ' + contacts.size());

    System.debug(LoggingLevel.INFO, '=== END processAccounts ===');
}
```

---

### Log Levels

| Level                   | When to Use       | Example                                                             |
| ----------------------- | ----------------- | ------------------------------------------------------------------- |
| `ERROR`                 | Critical failures | `System.debug(LoggingLevel.ERROR, 'DML failed: ' + e.getMessage())` |
| `WARN`                  | Potential issues  | `System.debug(LoggingLevel.WARN, 'No contacts found for account')`  |
| `INFO`                  | Key milestones    | `System.debug(LoggingLevel.INFO, 'Processing 251 accounts')`        |
| `DEBUG`                 | Detailed traces   | `System.debug(LoggingLevel.DEBUG, 'Variable value: ' + var)`        |
| `FINE`/`FINER`/`FINEST` | Very detailed     | Rarely used                                                         |

---

## Governor Limit Debugging

### Monitoring Limits in Code

```apex
public static void expensiveOperation() {
    System.debug('=== LIMIT CHECK ===');
    System.debug('SOQL Queries: ' + Limits.getQueries() + '/' + Limits.getLimitQueries());
    System.debug('DML Statements: ' + Limits.getDmlStatements() + '/' + Limits.getLimitDmlStatements());
    System.debug('DML Rows: ' + Limits.getDmlRows() + '/' + Limits.getLimitDmlRows());
    System.debug('CPU Time: ' + Limits.getCpuTime() + '/' + Limits.getLimitCpuTime());
    System.debug('Heap Size: ' + Limits.getHeapSize() + '/' + Limits.getLimitHeapSize());
}
```

---

### Common Limit Exceptions

**SOQL Limit (100 queries):**

```
System.LimitException: Too many SOQL queries: 101
```

**Fix**: Query BEFORE loops, use Maps for lookups.

**DML Limit (150 statements):**

```
System.LimitException: Too many DML statements: 151
```

**Fix**: Collect records in List, DML AFTER loop.

**CPU Time Limit (10 seconds):**

```
System.LimitException: Maximum CPU time exceeded
```

**Fix**: Optimize loops, move expensive operations to async, reduce complexity.

**Heap Size Limit (6 MB):**

```
System.LimitException: Apex heap size too large
```

**Fix**: Process in batches, clear collections when done, avoid storing large objects in memory.

---

### Using Limits Class for Alerts

```apex
public static void monitoredOperation() {
    // Warn if approaching 80% of limit
    Integer queriesUsed = Limits.getQueries();
    Integer queriesLimit = Limits.getLimitQueries();

    if (queriesUsed > queriesLimit * 0.8) {
        System.debug(LoggingLevel.WARN, 'Approaching SOQL limit: ' + queriesUsed + '/' + queriesLimit);
    }

    // Expensive operation
    List<Account> accounts = [SELECT Id FROM Account];
}
```

---

## Test Failures

### Common Test Failure Patterns

**Pattern 1: No assertions**

```apex
@IsTest
static void testCreateAccount() {
    Account acc = new Account(Name = 'Test');
    insert acc;
    // PASSES even if logic is broken!
}
```

**Fix**: Add assertions

```apex
@IsTest
static void testCreateAccount() {
    Account acc = new Account(Name = 'Test', Industry = 'Tech');
    insert acc;

    Account inserted = [SELECT Id, Industry FROM Account WHERE Id = :acc.Id];
    Assert.areEqual('Tech', inserted.Industry, 'Industry should be set');
}
```

---

**Pattern 2: Order dependency**

```apex
@IsTest
static void test1() {
    insert new Account(Name = 'Shared');
}

@IsTest
static void test2() {
    // Assumes test1 ran first - BRITTLE!
    Account acc = [SELECT Id FROM Account WHERE Name = 'Shared'];
}
```

**Fix**: Use @TestSetup or create data in each test

```apex
@TestSetup
static void setup() {
    insert new Account(Name = 'Shared');
}

@IsTest
static void test2() {
    Account acc = [SELECT Id FROM Account WHERE Name = 'Shared'];  // Safe
}
```

---

**Pattern 3: Insufficient permissions**

```apex
@IsTest
static void testRestrictedUser() {
    User u = TestDataFactory.createStandardUser();

    System.runAs(u) {
        // Fails if user lacks permission
        insert new Account(Name = 'Test');
    }
}
```

**Fix**: Grant necessary permissions

```apex
@TestSetup
static void setup() {
    User u = TestDataFactory.createStandardUser();
    insert new PermissionSetAssignment(
        AssigneeId = u.Id,
        PermissionSetId = [SELECT Id FROM PermissionSet WHERE Name = 'Account_Create'].Id
    );
}
```

---

### Running Tests

**VS Code:**

1. Open test class
2. Click "Run Test" above `@IsTest` method
3. View results in Output panel

**Via Salesforce MCP:**

```
# Test execution: use sf-testing skill or Salesforce Setup
# Run tests from Salesforce Setup → Apex Test Execution
# Or use Developer Console → Test → Run All
```

**Output:**

```
Test Summary
════════════
Outcome              Passed
Tests Ran            12
Pass Rate            100%
Fail Rate            0%
Skip Rate            0%
Test Run Coverage    92%
Org Wide Coverage    85%
Test Execution Time  1234 ms

Coverage Warnings
═════════════════
AccountService.cls  Line 45 not covered by tests
```

---

## Debugging Strategies

### 1. Binary Search for Errors

When unsure where error occurs, add debug statements at midpoints:

```apex
public static void complexOperation() {
    System.debug('START');

    // Part 1
    List<Account> accounts = [SELECT Id FROM Account];
    System.debug('CHECKPOINT 1: Retrieved ' + accounts.size() + ' accounts');

    // Part 2
    for (Account acc : accounts) {
        acc.Industry = 'Tech';
    }
    System.debug('CHECKPOINT 2: Updated accounts');

    // Part 3
    update accounts;
    System.debug('CHECKPOINT 3: DML complete');

    System.debug('END');
}
```

Run and check logs to see which checkpoint fails.

---

### 2. Isolate in Anonymous Apex

**Execute in Developer Console:**

```apex
Account acc = new Account(Name = 'Debug Test', Industry = 'Tech');
insert acc;

System.debug('Account ID: ' + acc.Id);
System.debug('Industry: ' + acc.Industry);
```

Open Execute Anonymous Window (`Ctrl+E`), paste code, check logs.

---

### 3. Unit Test in Isolation

**Create minimal test case:**

```apex
@IsTest
static void debugIssue() {
    Account acc = new Account(Name = 'Test', AnnualRevenue = null);

    Test.startTest();
    AccountService.calculateScore(acc);  // Isolated method
    Test.stopTest();

    System.debug('Score: ' + acc.Score__c);
}
```

Easier to debug than full integration test.

---

## Reference

**Full Documentation**: See `docs/` folder for comprehensive guides:

- `best-practices.md` - Debugging best practices
- `testing-guide.md` - Test troubleshooting
- `code-review-checklist.md` - Quality checklist

**Back to Main**: [SKILL.md](../SKILL.md)
