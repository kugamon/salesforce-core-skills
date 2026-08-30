/**
 * @description Minimal logger for orgs WITHOUT a logging framework. If Nebula
 *              Logger (or any other org-standard framework) is installed, use
 *              that instead — do not deploy this class alongside it.
 *
 *              Default sink is System.debug with a severity prefix and a
 *              per-transaction correlation id, so one transaction's entries
 *              can be grepped together in the debug log. No platform events,
 *              no custom objects required.
 *
 *              Pluggable sink: to persist entries, create a custom object
 *              (e.g. Log_Entry__c) and add an insert inside write() — keep
 *              this public API unchanged so call sites never move.
 *
 *              Governed by: sf-debug (log analysis) and sf-apex (error
 *              handling rubric — no empty catch blocks; log then handle).
 */
public inherited sharing class Logger {

    /** @description Correlation id shared by every entry in this transaction. */
    @TestVisible
    private static final String CORRELATION_ID =
        UserInfo.getUserId() + '-' +
        String.valueOf(Math.abs(Crypto.getRandomInteger())).left(8);

    /**
     * @description Logs a DEBUG-level message.
     * @param message text to log
     */
    public static void debug(String message) {
        write(LoggingLevel.DEBUG, message, null);
    }

    /**
     * @description Logs an INFO-level message.
     * @param message text to log
     */
    public static void info(String message) {
        write(LoggingLevel.INFO, message, null);
    }

    /**
     * @description Logs a WARN-level message.
     * @param message text to log
     */
    public static void warn(String message) {
        write(LoggingLevel.WARN, message, null);
    }

    /**
     * @description Logs an ERROR-level message.
     * @param message text to log
     */
    public static void error(String message) {
        write(LoggingLevel.ERROR, message, null);
    }

    /**
     * @description Logs an ERROR-level message with exception details.
     * @param message context for where/why the failure occurred
     * @param ex caught exception (type, message, stack trace are appended)
     */
    public static void error(String message, Exception ex) {
        write(LoggingLevel.ERROR, message, ex);
    }

    /**
     * @description Single sink for all entries. Swap or extend here (custom
     *              object insert, platform event) without touching call sites.
     * @param level severity for the debug log
     * @param message text to log
     * @param ex optional exception to include
     */
    private static void write(LoggingLevel level, String message, Exception ex) {
        String entry = '[' + level.name() + '] [txn:' + CORRELATION_ID + '] ' + message;
        if (ex != null) {
            entry += ' | ' + ex.getTypeName() + ': ' + ex.getMessage()
                + '\n' + ex.getStackTraceString();
        }
        System.debug(level, entry);
        // Pluggable sink example (requires Log_Entry__c):
        // insert as user new Log_Entry__c(Severity__c = level.name(),
        //     Correlation_Id__c = CORRELATION_ID, Message__c = entry.left(32768));
    }
}
