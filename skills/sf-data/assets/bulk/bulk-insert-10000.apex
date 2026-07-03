/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * BULK INSERT 10,000+ RECORDS
 * For Bulk API and large data volume testing
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * ⚠️  IMPORTANT: This script is designed to be run via Salesforce MCP server
 *     NOT via Anonymous Apex (which has governor limits)
 *
 * PURPOSE:
 * Generate large datasets for:
 * • Bulk API 2.0 testing
 * • Performance testing
 * • Data migration validation
 * • Report/Dashboard testing with realistic volumes
 *
 * APPROACHES:
 * 1. Use sobject_dml(operation="insert", ...) via Salesforce MCP (recommended)
 * 2. Use Data Loader for very large datasets
 * 3. Use batch Apex to create in smaller chunks
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// APPROACH 1: BATCH APEX FOR LARGE DATA CREATION
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Batch class to create large number of Account records
 * Execute with: Database.executeBatch(new BulkAccountCreator(10000), 200);
 */
public class BulkAccountCreator implements Database.Batchable<Integer>, Database.Stateful {

    private Integer targetCount;
    private Integer createdCount = 0;
    private String namePrefix;
    private List<String> industries;
    private DateTime startTime;

    public BulkAccountCreator(Integer count) {
        this.targetCount = count;
        this.namePrefix = 'BulkData';
        this.industries = new List<String>{
            'Technology', 'Healthcare', 'Finance', 'Manufacturing',
            'Retail', 'Education', 'Energy', 'Media'
        };
        this.startTime = DateTime.now();
    }

    public Iterable<Integer> start(Database.BatchableContext bc) {
        // Create list of indices to process
        List<Integer> indices = new List<Integer>();
        for (Integer i = 0; i < targetCount; i++) {
            indices.add(i);
        }
        return indices;
    }

    public void execute(Database.BatchableContext bc, List<Integer> indices) {
        List<Account> accounts = new List<Account>();

        for (Integer i : indices) {
            accounts.add(new Account(
                Name = namePrefix + '_' + String.valueOf(i).leftPad(7, '0'),
                Industry = industries[Math.mod(i, industries.size())],
                Type = Math.mod(i, 3) == 0 ? 'Customer' : 'Prospect',
                AnnualRevenue = 50000 + (Math.mod(i, 1000) * 1000),
                NumberOfEmployees = 10 + Math.mod(i, 1000),
                BillingCity = 'San Francisco',
                BillingState = 'CA',
                BillingCountry = 'USA',
                Description = 'Bulk created record ' + i
            ));
        }

        insert accounts;
        createdCount += accounts.size();
    }

    public void finish(Database.BatchableContext bc) {
        DateTime endTime = DateTime.now();
        Long durationMs = endTime.getTime() - startTime.getTime();

        System.debug('═══════════════════════════════════════════════════════════════');
        System.debug('BULK CREATION COMPLETE');
        System.debug('═══════════════════════════════════════════════════════════════');
        System.debug('Records Created: ' + createdCount);
        System.debug('Duration: ' + durationMs + 'ms (' + (durationMs / 1000) + ' seconds)');
        System.debug('Rate: ' + (createdCount * 1000 / durationMs) + ' records/second');
        System.debug('═══════════════════════════════════════════════════════════════');
    }
}

// Execute with:
// Database.executeBatch(new BulkAccountCreator(10000), 200);

// ═══════════════════════════════════════════════════════════════════════════════
// APPROACH 2: GENERATE DATA FOR BULK IMPORT
// Run this to generate records, then use sobject_dml(operation="insert", ...) via Salesforce MCP
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Generate CSV content for bulk import
 * Note: For very large files, generate externally with Python/Node.js
 */
public class BulkCsvGenerator {

    public static String generateAccountCsv(Integer count) {
        List<String> rows = new List<String>();

        // Header
        rows.add('Name,Industry,Type,AnnualRevenue,NumberOfEmployees,BillingCity,BillingState,BillingCountry,Description');

        List<String> industries = new List<String>{
            'Technology', 'Healthcare', 'Finance', 'Manufacturing',
            'Retail', 'Education', 'Energy', 'Media'
        };
        List<String> types = new List<String>{'Prospect', 'Customer', 'Partner'};

        // Data rows
        for (Integer i = 0; i < count; i++) {
            String name = 'BulkImport_' + String.valueOf(i).leftPad(7, '0');
            String industry = industries[Math.mod(i, industries.size())];
            String type = types[Math.mod(i, types.size())];
            Decimal revenue = 50000 + (Math.mod(i, 1000) * 1000);
            Integer employees = 10 + Math.mod(i, 1000);

            rows.add(String.join(new List<String>{
                name,
                industry,
                type,
                String.valueOf(revenue),
                String.valueOf(employees),
                'San Francisco',
                'CA',
                'USA',
                'Bulk imported record ' + i
            }, ','));
        }

        return String.join(rows, '\n');
    }
}

// Usage:
// String csv = BulkCsvGenerator.generateAccountCsv(1000);
// System.debug(csv);
// Then use: sobject_dml(operation="insert", sobjectType="Account", records=[...]) via Salesforce MCP

// ═══════════════════════════════════════════════════════════════════════════════
// SALESFORCE MCP MCP BULK IMPORT
// ═══════════════════════════════════════════════════════════════════════════════

/*
STEP 1: Prepare records as JSON

Example records:
[
  {"Name": "BulkTest_0000001", "Industry": "Technology", "Type": "Prospect", "AnnualRevenue": 100000, "BillingCity": "San Francisco", "BillingState": "CA", "BillingCountry": "USA"},
  {"Name": "BulkTest_0000002", "Industry": "Healthcare", "Type": "Customer", "AnnualRevenue": 150000, "BillingCity": "San Francisco", "BillingState": "CA", "BillingCountry": "USA"},
  ...
]

STEP 2: Import using Salesforce MCP server

sobject_dml(operation="insert", sobjectType="Account", records=[...])

*/

// ═══════════════════════════════════════════════════════════════════════════════
// PYTHON SCRIPT TO GENERATE LARGE CSV
// ═══════════════════════════════════════════════════════════════════════════════

/*
Save as generate_bulk_data.py:

import csv
import random

industries = ['Technology', 'Healthcare', 'Finance', 'Manufacturing',
              'Retail', 'Education', 'Energy', 'Media']
types = ['Prospect', 'Customer', 'Partner']
cities = ['San Francisco', 'New York', 'Chicago', 'Los Angeles', 'Seattle']
states = ['CA', 'NY', 'IL', 'CA', 'WA']

def generate_accounts(count, filename='accounts.csv'):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Industry', 'Type', 'AnnualRevenue',
                        'NumberOfEmployees', 'BillingCity', 'BillingState',
                        'BillingCountry', 'Description'])

        for i in range(count):
            city_idx = i % len(cities)
            writer.writerow([
                f'BulkTest_{i:07d}',
                industries[i % len(industries)],
                types[i % len(types)],
                50000 + (i % 1000) * 1000,
                10 + (i % 500),
                cities[city_idx],
                states[city_idx],
                'USA',
                f'Bulk test record {i}'
            ])

    print(f'Generated {count} records to {filename}')

if __name__ == '__main__':
    generate_accounts(10000)

Run: python generate_bulk_data.py
Then: sobject_dml(operation="insert", sobjectType="Account", records=[...]) via Salesforce MCP

*/

// ═══════════════════════════════════════════════════════════════════════════════
// CLEANUP FOR LARGE DATASETS
// ═══════════════════════════════════════════════════════════════════════════════

/*
CLEANUP via Salesforce MCP server:

Step 1: Query IDs to delete
soql_query(query="SELECT Id FROM Account WHERE Name LIKE 'BulkTest%' OR Name LIKE 'BulkData%' OR Name LIKE 'BulkImport%'")

Step 2: Delete records
sobject_dml(operation="delete", sobjectType="Account", records=[...])

For hard delete (permanent, requires permission):
sobject_dml(operation="hardDelete", sobjectType="Account", records=[...])
*/

// ═══════════════════════════════════════════════════════════════════════════════
// BATCH APEX CLEANUP
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Batch class to delete large number of records
 */
public class BulkRecordDeleter implements Database.Batchable<SObject> {

    private String query;

    public BulkRecordDeleter(String soqlQuery) {
        this.query = soqlQuery;
    }

    public Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator(query);
    }

    public void execute(Database.BatchableContext bc, List<SObject> records) {
        delete records;
    }

    public void finish(Database.BatchableContext bc) {
        System.debug('Bulk delete complete');
    }
}

// Execute with:
// String query = 'SELECT Id FROM Account WHERE Name LIKE \'BulkTest%\'';
// Database.executeBatch(new BulkRecordDeleter(query), 200);
