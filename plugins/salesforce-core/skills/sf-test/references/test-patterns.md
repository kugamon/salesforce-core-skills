# Apex Test Patterns

Copy-adapt patterns for the sf-test skill. All use the modern `Assert` class.

## TestDataFactory

One factory per org, `@IsTest public class TestDataFactory`. Methods return
unsaved records by default (callers control DML) with an `insert` convenience
variant:

```apex
@IsTest
public class TestDataFactory {
    public static List<Account> makeAccounts(Integer n) {
        List<Account> accts = new List<Account>();
        for (Integer i = 0; i < n; i++) {
            accts.add(new Account(Name = 'Test Account ' + i));
        }
        return accts;
    }
    public static List<Account> createAccounts(Integer n) {
        List<Account> accts = makeAccounts(n);
        insert accts;
        return accts;
    }
}
```

Add required-field defaults per object as the org's validation rules demand —
the factory is the single place to fix "REQUIRED_FIELD_MISSING" across the
whole test suite.

## @TestSetup

```apex
@TestSetup
static void setup() {
    insert TestDataFactory.makeAccounts(200);
}
```

Runs once per class; each test method gets a fresh rollback of this data.
Query for it inside the method (`[SELECT Id FROM Account]`) — don't cache in
static variables.

## Bulk pattern (the 200-record proof)

```apex
@IsTest
static void updatesAllAccountsInBulk() {
    List<Account> accts = [SELECT Id FROM Account];
    Assert.areEqual(200, accts.size(), 'Setup should create 200 accounts');

    Test.startTest();
    AccountService.applyRegionAssignment(accts);
    Test.stopTest();

    Integer assigned = [SELECT COUNT() FROM Account WHERE Region__c != null];
    Assert.areEqual(200, assigned, 'Every account should get a region — a partial count means the code path is not bulk-safe');
}
```

Assert over the FULL set. Asserting on `accts[0]` only proves the code works
for one record — the exact thing bulk tests exist to disprove.

## runAs (permission enforcement)

```apex
@IsTest
static void deniesUpdateWithoutPermission() {
    User restricted = TestUserFactory.createMinimalUser(); // profile with no Account edit
    System.runAs(restricted) {
        Account a = [SELECT Id FROM Account LIMIT 1];
        try {
            AccountService.rename(a.Id, 'New Name');
            Assert.fail('Expected SecurityException for user without edit access');
        } catch (SecurityException e) {
            Assert.isTrue(e.getMessage().contains('Account'), 'Exception should name the blocked object');
        }
    }
}
```

Test BOTH directions: the restricted user is denied AND the permitted user
succeeds. One without the other proves half the requirement.

## HttpCalloutMock

```apex
@IsTest
private class PaymentGatewayMock implements HttpCalloutMock {
    public HTTPResponse respond(HTTPRequest req) {
        Assert.isTrue(req.getEndpoint().contains('callout:Payment_NC'),
            'Callout must use the named credential, not a hardcoded endpoint');
        HttpResponse res = new HttpResponse();
        res.setStatusCode(200);
        res.setBody('{"status":"approved","id":"txn-123"}');
        return res;
    }
}

@IsTest
static void processesApprovedPayment() {
    Test.setMock(HttpCalloutMock.class, new PaymentGatewayMock());
    Test.startTest();
    PaymentResult r = PaymentService.charge(100.00);
    Test.stopTest();
    Assert.areEqual('approved', r.status, 'Mock approval should map to result status');
}
```

Asserting on the request inside the mock catches endpoint/auth regressions
for free.

## Async patterns

```apex
// Queueable / future: stopTest() forces synchronous completion
Test.startTest();
System.enqueueJob(new RegionAssignmentQueueable(acctIds));
Test.stopTest();
// assert results here — the job HAS run

// Batch: run with a bounded scope
Test.startTest();
Database.executeBatch(new AccountCleanupBatch(), 200);
Test.stopTest();

// Platform events
Test.startTest();
EventBus.publish(new Order_Placed__e(Order_Id__c = 'O-1'));
Test.getEventBus().deliver();   // fire subscribers now
Test.stopTest();

// Schedulable: assert the cron registration, then test execute() directly
String jobId = System.schedule('nightly', '0 0 2 * * ?', new NightlySync());
CronTrigger ct = [SELECT CronExpression FROM CronTrigger WHERE Id = :jobId];
Assert.areEqual('0 0 2 * * ?', ct.CronExpression, 'Cron should register as scheduled');
```

## Stub API (isolating dependencies)

```apex
@IsTest
private class SelectorStub implements System.StubProvider {
    public Object handleMethodCall(Object stubbed, String method, Type returnType,
            List<Type> paramTypes, List<String> paramNames, List<Object> args) {
        if (method == 'selectActive') {
            return new List<Account>{ new Account(Name = 'Stubbed') };
        }
        return null;
    }
}

AccountSelector stub = (AccountSelector) Test.createStub(AccountSelector.class, new SelectorStub());
AccountService svc = new AccountService(stub);   // constructor injection
```

Use stubs when the dependency does SOQL/DML you don't want in a unit test.
Requires the production class to accept injected dependencies — if it
doesn't, that's an sf-apex refactor recommendation, not a test workaround.

## Exception-path sentinel

```apex
try {
    InvoiceService.post(null);
    Assert.fail('Expected IllegalArgumentException for null invoice');
} catch (IllegalArgumentException e) {
    Assert.isTrue(e.getMessage().contains('invoice'), 'Message should identify the bad argument');
}
```

The `Assert.fail()` sentinel is mandatory — without it, a silently-passing
happy path masquerades as a negative test.

## What NOT to write

- Methods with no assertions ("coverage tests") — rejected in review, 0 points
- `SeeAllData=true` without a documented org-data dependency
- Asserting only `!= null` on complex results
- One giant `testEverything()` method — one concern per method
- `Test.isRunningTest()` branches in production code to dodge logic — that's
  testing a different program
