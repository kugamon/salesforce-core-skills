/**
 * @description Lean, dependency-free one-trigger-per-object handler base class.
 *              The lightweight alternative when the Trigger Actions Framework
 *              (TAF) is overkill or a package dependency is unwanted.
 *
 *              Usage: subclass per object (e.g. AccountTriggerHandler extends
 *              TriggerHandler), override only the contexts the object needs,
 *              and wire a one-line-body trigger that calls run() — see
 *              AccountTrigger.trigger alongside this file.
 *
 *              Provides: context routing, a static bypass flag (data loads,
 *              test isolation), and an OPT-IN per-handler recursion guard
 *              (call setMaxRecursion() to enable; off by default so every
 *              context and every 200-record DML chunk runs).
 *
 *              Governed by: sf-apex. Keep ALL logic out of the trigger body;
 *              handler overrides should delegate real work to service classes.
 */
public virtual inherited sharing class TriggerHandler {

    /** @description Handler names bypassed for the rest of the transaction. */
    private static Set<String> bypassedHandlers = new Set<String>();

    /** @description Executions per handler in this transaction (recursion guard). */
    private static Map<String, Integer> runCounts = new Map<String, Integer>();

    /**
     * @description Optional recursion ceiling. Null (the default) means NO
     *              limit — all contexts and all DML chunks run. Only enforced
     *              when a subclass opts in via setMaxRecursion().
     */
    private Integer maxRecursion = null;

    /**
     * @description Entry point called from the trigger body. Applies bypass and
     *              recursion checks, then routes the live Trigger context to the
     *              matching virtual method.
     */
    public void run() {
        if (!Trigger.isExecuting) {
            return;
        }
        String name = handlerName();
        if (bypassedHandlers.contains(name)) {
            return;
        }
        if (maxRecursion != null) {
            Integer runs = runCounts.containsKey(name) ? runCounts.get(name) : 0;
            if (runs >= maxRecursion) {
                return;
            }
            runCounts.put(name, runs + 1);
        }

        if (Trigger.isBefore) {
            if (Trigger.isInsert) {
                beforeInsert(Trigger.new);
            } else if (Trigger.isUpdate) {
                beforeUpdate(Trigger.new, Trigger.oldMap);
            } else if (Trigger.isDelete) {
                beforeDelete(Trigger.old);
            }
        } else if (Trigger.isAfter) {
            if (Trigger.isInsert) {
                afterInsert(Trigger.new);
            } else if (Trigger.isUpdate) {
                afterUpdate(Trigger.new, Trigger.oldMap);
            } else if (Trigger.isDelete) {
                afterDelete(Trigger.old);
            } else if (Trigger.isUndelete) {
                afterUndelete(Trigger.new);
            }
        }
    }

    /**
     * @description Bypasses a handler for the rest of the transaction. Use for
     *              bulk data loads or test setup — never as a design crutch.
     * @param handlerName concrete subclass name, e.g. 'AccountTriggerHandler'
     */
    public static void bypass(String handlerName) {
        bypassedHandlers.add(handlerName);
    }

    /**
     * @description Re-enables a handler bypassed earlier in the transaction.
     * @param handlerName concrete subclass name to re-enable
     */
    public static void clearBypass(String handlerName) {
        bypassedHandlers.remove(handlerName);
    }

    /**
     * @description Reports whether a handler is currently bypassed.
     * @param handlerName concrete subclass name to check
     * @return true when the handler will skip execution
     */
    public static Boolean isBypassed(String handlerName) {
        return bypassedHandlers.contains(handlerName);
    }

    /**
     * @description Opts this handler in to the recursion guard. No limit is
     *              enforced unless a subclass calls this. CAUTION: every
     *              trigger invocation counts as one run — each context
     *              (before insert, after insert, ...) and each 200-record DML
     *              chunk consumes an entry, so size the ceiling accordingly
     *              (e.g. a handler wired for before+after needs at least 2 per
     *              expected pass). Prefer a processed-Id Set inside the
     *              handler when you only need to stop re-fired updates.
     * @param maxRuns maximum trigger invocations allowed per transaction
     */
    protected void setMaxRecursion(Integer maxRuns) {
        this.maxRecursion = maxRuns;
    }

    /**
     * @description Resolves the concrete subclass name for bookkeeping.
     * @return the runtime class name of this handler instance
     */
    private String handlerName() {
        return String.valueOf(this).split(':')[0];
    }

    // Context methods — override only what the object needs.

    /** @description Override for before insert logic. @param newList Trigger.new */
    protected virtual void beforeInsert(List<SObject> newList) {}

    /** @description Override for before update logic. @param newList Trigger.new @param oldMap Trigger.oldMap */
    protected virtual void beforeUpdate(List<SObject> newList, Map<Id, SObject> oldMap) {}

    /** @description Override for before delete logic. @param oldList Trigger.old */
    protected virtual void beforeDelete(List<SObject> oldList) {}

    /** @description Override for after insert logic. @param newList Trigger.new */
    protected virtual void afterInsert(List<SObject> newList) {}

    /** @description Override for after update logic. @param newList Trigger.new @param oldMap Trigger.oldMap */
    protected virtual void afterUpdate(List<SObject> newList, Map<Id, SObject> oldMap) {}

    /** @description Override for after delete logic. @param oldList Trigger.old */
    protected virtual void afterDelete(List<SObject> oldList) {}

    /** @description Override for after undelete logic. @param newList Trigger.new */
    protected virtual void afterUndelete(List<SObject> newList) {}
}
