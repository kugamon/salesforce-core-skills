# Credits

## Adaptation (2026)

This plugin was adapted from the [sf-permissions](https://github.com/Jaganpro/sf-skills/tree/main/skills/sf-permissions) plugin published by Jag Valaiyapathy

It was subsequently generalized to work with any Salesforce MCP server and AI coding tools.

See below for original credits and attribution.

---

## Original Credits

## PSLab - Permission Set Lab

This skill was inspired by **PSLab**, an open-source Salesforce permission analysis tool created by **Oumaima Arbani**.

- **GitHub**: [github.com/OumArbani/PSLab](https://github.com/OumArbani/PSLab)
- **Author**: Oumaima Arbani
- **License**: MIT

### What We Learned from PSLab

PSLab's Apex implementation provided the conceptual foundation for permission analysis:

1. **Permission Hierarchy Visualization** - The tree structure approach for showing PS/PSG relationships
2. **Permission Detection Queries** - The SOQL patterns for finding "who has access to X"
3. **User Permission Analysis** - The approach to tracing permissions through PSG membership
4. **Setup Entity Access** - How to query Apex class, VF page, and Custom Permission access

### License Compliance

This skill is a clean-room reimplementation of PSLab's concepts using Salesforce MCP tools. No code was directly copied. The SOQL query patterns are based on standard Salesforce APIs.

---

## Other Resources

### Salesforce Documentation

- [Permission Sets Developer Guide](https://developer.salesforce.com/docs/atlas.en-us.securityImplGuide.meta/securityImplGuide/perm_sets_overview.htm)
- [Permission Set Groups](https://help.salesforce.com/s/articleView?id=sf.perm_set_groups.htm)
- [SetupEntityAccess Object](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_setupentityaccess.htm)

---

_If we've missed anyone whose work influenced this skill, please let us know so we can add proper attribution._
