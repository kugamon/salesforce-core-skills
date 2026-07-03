/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * DELETE RECORDS BY CREATED DATE
 * Clean up test records created within a specific time window
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * PURPOSE:
 * Delete records created during a testing session or time period.
 * Useful when you know the approximate time test data was created.
 *
 * ⚠️  WARNING:
 * Always PREVIEW records before deleting!
 * Be careful with date ranges - you might delete production data!
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

// Time window for records to delete
DateTime startTime = DateTime.now().addHours(-2);  // 2 hours ago
DateTime endTime = DateTime.now();                  // Now

// Optional: Add name pattern for extra safety
String namePattern = 'Test%';  // Set to null to skip name filter
Boolean useNameFilter = true;  // Set to false to delete ALL records in time window

Boolean previewOnly = true;    // Set to false to actually delete
Integer maxRecords = 10000;    // Safety limit per object

// ═══════════════════════════════════════════════════════════════════════════════
// BUILD DYNAMIC QUERY CONDITIONS
// ═══════════════════════════════════════════════════════════════════════════════

String dateCondition = 'CreatedDate >= :startTime AND CreatedDate <= :endTime';

System.debug('═══════════════════════════════════════════════════════════════');
System.debug('DELETE BY CREATED DATE');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('Time Window:');
System.debug('  Start: ' + startTime.format('yyyy-MM-dd HH:mm:ss'));
System.debug('  End:   ' + endTime.format('yyyy-MM-dd HH:mm:ss'));
if (useNameFilter) {
    System.debug('Name Filter: ' + namePattern);
}
System.debug('Mode: ' + (previewOnly ? 'PREVIEW ONLY' : '⚠️  DELETE MODE'));
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 1: PREVIEW ACCOUNTS
// ═══════════════════════════════════════════════════════════════════════════════

List<Account> accountsToDelete;
if (useNameFilter) {
    accountsToDelete = [
        SELECT Id, Name, CreatedDate, CreatedBy.Name
        FROM Account
        WHERE CreatedDate >= :startTime
        AND CreatedDate <= :endTime
        AND Name LIKE :namePattern
        ORDER BY CreatedDate DESC
        LIMIT :maxRecords
    ];
} else {
    accountsToDelete = [
        SELECT Id, Name, CreatedDate, CreatedBy.Name
        FROM Account
        WHERE CreatedDate >= :startTime
        AND CreatedDate <= :endTime
        ORDER BY CreatedDate DESC
        LIMIT :maxRecords
    ];
}

System.debug('📋 ACCOUNTS in time window: ' + accountsToDelete.size());
if (!accountsToDelete.isEmpty()) {
    System.debug('   Records:');
    for (Integer i = 0; i < Math.min(10, accountsToDelete.size()); i++) {
        Account acc = accountsToDelete[i];
        System.debug('   - ' + acc.Name + ' (Created: ' + acc.CreatedDate.format('HH:mm:ss') + ' by ' + acc.CreatedBy.Name + ')');
    }
    if (accountsToDelete.size() > 10) {
        System.debug('   ... and ' + (accountsToDelete.size() - 10) + ' more');
    }
}
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 2: PREVIEW CONTACTS
// ═══════════════════════════════════════════════════════════════════════════════

List<Contact> contactsToDelete;
if (useNameFilter) {
    contactsToDelete = [
        SELECT Id, FirstName, LastName, Account.Name, CreatedDate, CreatedBy.Name
        FROM Contact
        WHERE CreatedDate >= :startTime
        AND CreatedDate <= :endTime
        AND (LastName LIKE :namePattern OR Account.Name LIKE :namePattern)
        ORDER BY CreatedDate DESC
        LIMIT :maxRecords
    ];
} else {
    contactsToDelete = [
        SELECT Id, FirstName, LastName, Account.Name, CreatedDate, CreatedBy.Name
        FROM Contact
        WHERE CreatedDate >= :startTime
        AND CreatedDate <= :endTime
        ORDER BY CreatedDate DESC
        LIMIT :maxRecords
    ];
}

System.debug('📋 CONTACTS in time window: ' + contactsToDelete.size());
if (!contactsToDelete.isEmpty()) {
    System.debug('   Records:');
    for (Integer i = 0; i < Math.min(5, contactsToDelete.size()); i++) {
        Contact con = contactsToDelete[i];
        System.debug('   - ' + con.FirstName + ' ' + con.LastName + ' (Created: ' + con.CreatedDate.format('HH:mm:ss') + ')');
    }
}
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 3: PREVIEW OPPORTUNITIES
// ═══════════════════════════════════════════════════════════════════════════════

List<Opportunity> opportunitiesToDelete;
if (useNameFilter) {
    opportunitiesToDelete = [
        SELECT Id, Name, Account.Name, StageName, Amount, CreatedDate
        FROM Opportunity
        WHERE CreatedDate >= :startTime
        AND CreatedDate <= :endTime
        AND (Name LIKE :namePattern OR Account.Name LIKE :namePattern)
        ORDER BY CreatedDate DESC
        LIMIT :maxRecords
    ];
} else {
    opportunitiesToDelete = [
        SELECT Id, Name, Account.Name, StageName, Amount, CreatedDate
        FROM Opportunity
        WHERE CreatedDate >= :startTime
        AND CreatedDate <= :endTime
        ORDER BY CreatedDate DESC
        LIMIT :maxRecords
    ];
}

System.debug('📋 OPPORTUNITIES in time window: ' + opportunitiesToDelete.size());
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 4: PREVIEW TASKS
// ═══════════════════════════════════════════════════════════════════════════════

List<Task> tasksToDelete;
if (useNameFilter) {
    tasksToDelete = [
        SELECT Id, Subject, Status, CreatedDate
        FROM Task
        WHERE CreatedDate >= :startTime
        AND CreatedDate <= :endTime
        AND Subject LIKE :namePattern
        ORDER BY CreatedDate DESC
        LIMIT :maxRecords
    ];
} else {
    tasksToDelete = [
        SELECT Id, Subject, Status, CreatedDate
        FROM Task
        WHERE CreatedDate >= :startTime
        AND CreatedDate <= :endTime
        ORDER BY CreatedDate DESC
        LIMIT :maxRecords
    ];
}

System.debug('📋 TASKS in time window: ' + tasksToDelete.size());
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 5: PREVIEW LEADS
// ═══════════════════════════════════════════════════════════════════════════════

List<Lead> leadsToDelete;
if (useNameFilter) {
    leadsToDelete = [
        SELECT Id, FirstName, LastName, Company, Status, CreatedDate
        FROM Lead
        WHERE CreatedDate >= :startTime
        AND CreatedDate <= :endTime
        AND (LastName LIKE :namePattern OR Company LIKE :namePattern)
        ORDER BY CreatedDate DESC
        LIMIT :maxRecords
    ];
} else {
    leadsToDelete = [
        SELECT Id, FirstName, LastName, Company, Status, CreatedDate
        FROM Lead
        WHERE CreatedDate >= :startTime
        AND CreatedDate <= :endTime
        ORDER BY CreatedDate DESC
        LIMIT :maxRecords
    ];
}

System.debug('📋 LEADS in time window: ' + leadsToDelete.size());
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// SUMMARY
// ═══════════════════════════════════════════════════════════════════════════════

Integer totalRecords = accountsToDelete.size() + contactsToDelete.size() +
                       opportunitiesToDelete.size() + tasksToDelete.size() +
                       leadsToDelete.size();

System.debug('═══════════════════════════════════════════════════════════════');
System.debug('SUMMARY - Records in time window');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('  Accounts:      ' + accountsToDelete.size());
System.debug('  Contacts:      ' + contactsToDelete.size());
System.debug('  Opportunities: ' + opportunitiesToDelete.size());
System.debug('  Tasks:         ' + tasksToDelete.size());
System.debug('  Leads:         ' + leadsToDelete.size());
System.debug('  ─────────────────────────────────');
System.debug('  TOTAL:         ' + totalRecords);
System.debug('═══════════════════════════════════════════════════════════════');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 6: DELETE (if not preview mode)
// ═══════════════════════════════════════════════════════════════════════════════

if (!previewOnly && totalRecords > 0) {
    System.debug('');
    System.debug('⚠️  DELETING RECORDS...');

    Integer deletedCount = 0;

    // Delete in correct order (children first, then parents)
    if (!tasksToDelete.isEmpty()) {
        delete tasksToDelete;
        deletedCount += tasksToDelete.size();
        System.debug('  ✓ Deleted ' + tasksToDelete.size() + ' Tasks');
    }

    if (!opportunitiesToDelete.isEmpty()) {
        delete opportunitiesToDelete;
        deletedCount += opportunitiesToDelete.size();
        System.debug('  ✓ Deleted ' + opportunitiesToDelete.size() + ' Opportunities');
    }

    if (!contactsToDelete.isEmpty()) {
        delete contactsToDelete;
        deletedCount += contactsToDelete.size();
        System.debug('  ✓ Deleted ' + contactsToDelete.size() + ' Contacts');
    }

    if (!leadsToDelete.isEmpty()) {
        delete leadsToDelete;
        deletedCount += leadsToDelete.size();
        System.debug('  ✓ Deleted ' + leadsToDelete.size() + ' Leads');
    }

    if (!accountsToDelete.isEmpty()) {
        delete accountsToDelete;
        deletedCount += accountsToDelete.size();
        System.debug('  ✓ Deleted ' + accountsToDelete.size() + ' Accounts');
    }

    System.debug('');
    System.debug('═══════════════════════════════════════════════════════════════');
    System.debug('DELETE COMPLETE: ' + deletedCount + ' records moved to Recycle Bin');
    System.debug('═══════════════════════════════════════════════════════════════');
} else if (previewOnly) {
    System.debug('');
    System.debug('ℹ️  PREVIEW MODE - No records deleted');
    System.debug('   To delete, set previewOnly = false and run again');
}

// ═══════════════════════════════════════════════════════════════════════════════
// SALESFORCE MCP MCP ALTERNATIVE WITH DATE LITERALS
// ═══════════════════════════════════════════════════════════════════════════════

/*
Using SOQL date literals via Salesforce MCP server:

Records created today:
soql_query(query="SELECT Id FROM Account WHERE CreatedDate = TODAY AND Name LIKE 'Test%'")

Records created in the last hour:
soql_query(query="SELECT Id FROM Account WHERE CreatedDate = LAST_N_HOURS:1 AND Name LIKE 'Test%'")

Records created this week:
soql_query(query="SELECT Id FROM Account WHERE CreatedDate = THIS_WEEK AND Name LIKE 'Test%'")

Then delete the records:
sobject_dml(operation="delete", sobjectType="Account", records=[...])
*/
