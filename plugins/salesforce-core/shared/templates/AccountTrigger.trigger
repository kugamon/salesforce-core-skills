// Example wiring for TriggerHandler.cls: one trigger per object, zero logic
// in the body. AccountTriggerHandler extends TriggerHandler and overrides
// only the contexts Account needs.
trigger AccountTrigger on Account (before insert, before update, before delete,
        after insert, after update, after delete, after undelete) {
    new AccountTriggerHandler().run();
}
