/**
 * @description Central test data factory — the single place where required
 *              fields and validation-rule prerequisites are satisfied for the
 *              whole test suite. make* methods return UNSAVED records so
 *              callers control DML; create* variants insert and return.
 *
 *              Copy into the org and extend one make/create pair per object.
 *              When a new validation rule breaks tests, fix it once in
 *              applyDefaults(), not in fifty test classes.
 *
 *              Governed by: sf-test (see that skill's test-patterns reference
 *              for usage with @TestSetup and the bulk/runAs patterns).
 */
@IsTest
public class TestDataFactory {

    /**
     * @description Builds unsaved Accounts with unique names and org defaults.
     * @param count number of records to build
     * @return unsaved Account list (caller performs DML)
     */
    public static List<Account> makeAccounts(Integer count) {
        List<Account> accounts = new List<Account>();
        for (Integer i = 0; i < count; i++) {
            Account acc = new Account(Name = 'Test Account ' + i);
            applyDefaults(acc);
            accounts.add(acc);
        }
        return accounts;
    }

    /**
     * @description Inserts and returns Accounts built by makeAccounts.
     * @param count number of records to create
     * @return inserted Account list with Ids populated
     */
    public static List<Account> createAccounts(Integer count) {
        List<Account> accounts = makeAccounts(count);
        insert accounts;
        return accounts;
    }

    /**
     * @description Builds unsaved Contacts parented to the given Account.
     * @param count number of records to build
     * @param accountId parent Account Id (null allowed for orphan contacts)
     * @return unsaved Contact list (caller performs DML)
     */
    public static List<Contact> makeContacts(Integer count, Id accountId) {
        List<Contact> contacts = new List<Contact>();
        for (Integer i = 0; i < count; i++) {
            Contact con = new Contact(
                LastName = 'TestContact ' + i,
                AccountId = accountId
            );
            applyDefaults(con);
            contacts.add(con);
        }
        return contacts;
    }

    /**
     * @description Inserts and returns Contacts built by makeContacts.
     * @param count number of records to create
     * @param accountId parent Account Id
     * @return inserted Contact list with Ids populated
     */
    public static List<Contact> createContacts(Integer count, Id accountId) {
        List<Contact> contacts = makeContacts(count, accountId);
        insert contacts;
        return contacts;
    }

    /**
     * @description Required-field defaults hook — the ONE place to satisfy
     *              org-specific required fields and validation rules. Extend
     *              the switch as the factory grows to new objects.
     * @param record unsaved record to decorate before return
     */
    private static void applyDefaults(SObject record) {
        switch on record {
            when Account acc {
                // e.g. acc.Industry = 'Technology'; acc.BillingCountry = 'USA';
            }
            when Contact con {
                // e.g. con.Email = 'test' + con.LastName.deleteWhitespace() + '@example.invalid';
            }
            when else {
                // Add a case per object as org validation rules demand.
            }
        }
    }
}
