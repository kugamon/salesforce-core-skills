#!/usr/bin/env bash
#
# extract_data.sh — Bulk data extraction for Salesforce org audit (CLI mode)
#
# Pulls raw metadata and SOQL results via the Salesforce CLI (`sf`).
# Only used when EXEC_MODE=cli (CLI is authenticated and org-aligned).
# In cloud mode the AI agent extracts data via MCP tools instead.
#
# Usage:
#   ./extract_data.sh --target-org <alias-or-username> [--output-dir audit_output]
#
# Outputs:
#   <output-dir>/counts.json           — component inventory counts
#   <output-dir>/raw/                  — raw JSON query results
#   <output-dir>/intermediate/apex/    — Apex class .cls files
#   <output-dir>/intermediate/triggers/— Apex trigger .trigger files
#   <output-dir>/intermediate/flows/   — Flow .flow-meta.xml files
#   <output-dir>/intermediate/lwc/     — LWC component bundles
#
# Prerequisites:
#   - Salesforce CLI (sf) installed and authenticated
#   - Target org reachable (run environment detection first)

set -euo pipefail

# ── Argument parsing ────────────────────────────────────────────────────────

TARGET_ORG=""
OUTPUT_DIR="audit_output"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-org)   TARGET_ORG="$2"; shift 2 ;;
    --output-dir)   OUTPUT_DIR="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 --target-org <alias-or-username> [--output-dir audit_output]"
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$TARGET_ORG" ]]; then
  echo "ERROR: --target-org is required" >&2
  exit 1
fi

# ── Setup ───────────────────────────────────────────────────────────────────

RAW_DIR="$OUTPUT_DIR/raw"
mkdir -p "$RAW_DIR" \
  "$OUTPUT_DIR/intermediate/apex" \
  "$OUTPUT_DIR/intermediate/triggers" \
  "$OUTPUT_DIR/intermediate/flows" \
  "$OUTPUT_DIR/intermediate/lwc" \
  "$OUTPUT_DIR/intermediate/permissions" \
  "$OUTPUT_DIR/intermediate/metadata"

HAS_JQ=false
if command -v jq >/dev/null 2>&1; then
  HAS_JQ=true
fi

# Helper: run a SOQL/Tooling query via CLI and save raw JSON
# Stdout (JSON) goes to outfile; stderr is captured and shown on failure.
query_tooling() {
  local soql="$1"
  local outfile="$2"
  local tmp_err
  tmp_err="$(mktemp)"
  if ! sf data query --use-tooling-api \
    -q "$soql" \
    --target-org "$TARGET_ORG" \
    --json \
    > "$outfile" 2>"$tmp_err"; then
    echo "WARNING: Tooling API query failed: $soql" >&2
    [[ -s "$tmp_err" ]] && cat "$tmp_err" >&2
  fi
  rm -f "$tmp_err"
}

query_soql() {
  local soql="$1"
  local outfile="$2"
  local tmp_err
  tmp_err="$(mktemp)"
  if ! sf data query \
    -q "$soql" \
    --target-org "$TARGET_ORG" \
    --json \
    > "$outfile" 2>"$tmp_err"; then
    echo "WARNING: SOQL query failed: $soql" >&2
    [[ -s "$tmp_err" ]] && cat "$tmp_err" >&2
  fi
  rm -f "$tmp_err"
}

# Helper: extract count from CLI JSON output
extract_count() {
  local file="$1"
  if $HAS_JQ; then
    jq -r '.result.records[0].expr0 // 0' "$file" 2>/dev/null || echo "0"
  else
    python3 -c "
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    recs = d.get('result', {}).get('records', [])
    print(recs[0].get('expr0', 0) if recs else 0)
except Exception:
    print(0)
" "$file" 2>/dev/null || echo "0"
  fi
}

echo "=== Salesforce Org Audit — Data Extraction ==="
echo "Target org: $TARGET_ORG"
echo "Output dir: $OUTPUT_DIR"
echo ""

# ── Phase 1: Inventory counts ──────────────────────────────────────────────

echo "Phase 1: Collecting inventory counts..."

query_tooling "SELECT COUNT(Id) FROM ApexClass WHERE NamespacePrefix = null" \
  "$RAW_DIR/count_apex_classes.json"

query_tooling "SELECT COUNT(Id) FROM ApexTrigger WHERE NamespacePrefix = null" \
  "$RAW_DIR/count_apex_triggers.json"

query_tooling "SELECT COUNT(Id) FROM FlowDefinition WHERE ActiveVersionId != null AND NamespacePrefix = null" \
  "$RAW_DIR/count_active_flows.json"

# Process Builders: active Flows with ProcessType = 'Workflow'
query_tooling "SELECT COUNT(Id) FROM Flow WHERE Status = 'Active' AND ProcessType = 'Workflow' AND NamespacePrefix = null" \
  "$RAW_DIR/count_process_builders.json"

query_tooling "SELECT COUNT(Id) FROM LightningComponentBundle WHERE NamespacePrefix = null" \
  "$RAW_DIR/count_lwc_bundles.json"

query_tooling "SELECT COUNT(Id) FROM CustomObject WHERE NamespacePrefix = null" \
  "$RAW_DIR/count_custom_objects.json"

query_tooling "SELECT COUNT(Id) FROM ValidationRule WHERE NamespacePrefix = null" \
  "$RAW_DIR/count_validation_rules.json"

query_tooling "SELECT COUNT(Id) FROM WorkflowRule WHERE NamespacePrefix = null" \
  "$RAW_DIR/count_workflow_rules.json"

query_soql "SELECT COUNT(Id) FROM PermissionSet WHERE IsOwnedByProfile = false AND NamespacePrefix = null AND Type != 'Group'" \
  "$RAW_DIR/count_permission_sets.json"

query_soql "SELECT COUNT(Id) FROM PermissionSetGroup" \
  "$RAW_DIR/count_permission_set_groups.json"

query_soql "SELECT COUNT(Id) FROM Profile" \
  "$RAW_DIR/count_profiles.json"

query_soql "SELECT COUNT(Id) FROM User WHERE IsActive = true" \
  "$RAW_DIR/count_active_users.json"

# Build counts.json
APEX_CLASSES=$(extract_count "$RAW_DIR/count_apex_classes.json")
APEX_TRIGGERS=$(extract_count "$RAW_DIR/count_apex_triggers.json")
ACTIVE_FLOWS=$(extract_count "$RAW_DIR/count_active_flows.json")
PROCESS_BUILDERS=$(extract_count "$RAW_DIR/count_process_builders.json")
LWC_BUNDLES=$(extract_count "$RAW_DIR/count_lwc_bundles.json")
CUSTOM_OBJECTS=$(extract_count "$RAW_DIR/count_custom_objects.json")
VALIDATION_RULES=$(extract_count "$RAW_DIR/count_validation_rules.json")
WORKFLOW_RULES=$(extract_count "$RAW_DIR/count_workflow_rules.json")
PERMISSION_SETS=$(extract_count "$RAW_DIR/count_permission_sets.json")
PERMISSION_SET_GROUPS=$(extract_count "$RAW_DIR/count_permission_set_groups.json")
PROFILES=$(extract_count "$RAW_DIR/count_profiles.json")
ACTIVE_USERS=$(extract_count "$RAW_DIR/count_active_users.json")

# Get org info
ORG_INFO=$(sf org display --target-org "$TARGET_ORG" --json 2>/dev/null || echo '{}')
if $HAS_JQ; then
  ORG_NAME=$(echo "$ORG_INFO" | jq -r '.result.alias // .result.username // ""')
  ORG_ID=$(echo "$ORG_INFO" | jq -r '.result.id // ""')
  INSTANCE=$(echo "$ORG_INFO" | jq -r '.result.instanceUrl // ""' | sed 's|https://||;s|\..*||')
else
  ORG_NAME=$(python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
r = d.get('result', {})
print(r.get('alias', r.get('username', '')))
" <<< "$ORG_INFO" 2>/dev/null || echo "")
  ORG_ID=$(python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
print(d.get('result', {}).get('id', ''))
" <<< "$ORG_INFO" 2>/dev/null || echo "")
  INSTANCE=$(python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
url = d.get('result', {}).get('instanceUrl', '')
print(url.replace('https://', '').split('.')[0] if url else '')
" <<< "$ORG_INFO" 2>/dev/null || echo "")
fi

# Build counts.json via Python to ensure proper JSON escaping of string values
python3 -c "
import json, sys
data = {
    'org_name': sys.argv[1],
    'org_id': sys.argv[2],
    'instance': sys.argv[3],
    'apex_classes': int(sys.argv[4]),
    'apex_triggers': int(sys.argv[5]),
    'active_flows': int(sys.argv[6]),
    'process_builders': int(sys.argv[7]),
    'lwc_bundles': int(sys.argv[8]),
    'custom_objects': int(sys.argv[9]),
    'validation_rules': int(sys.argv[10]),
    'workflow_rules': int(sys.argv[11]),
    'permission_sets': int(sys.argv[12]),
    'permission_set_groups': int(sys.argv[13]),
    'profiles': int(sys.argv[14]),
    'active_users': int(sys.argv[15]),
}
with open(sys.argv[16], 'w') as f:
    json.dump(data, f, indent=2)
" "$ORG_NAME" "$ORG_ID" "$INSTANCE" \
  "$APEX_CLASSES" "$APEX_TRIGGERS" "$ACTIVE_FLOWS" "$PROCESS_BUILDERS" \
  "$LWC_BUNDLES" "$CUSTOM_OBJECTS" "$VALIDATION_RULES" "$WORKFLOW_RULES" \
  "$PERMISSION_SETS" "$PERMISSION_SET_GROUPS" "$PROFILES" "$ACTIVE_USERS" \
  "$OUTPUT_DIR/counts.json"

echo "  Inventory: $APEX_CLASSES Apex classes, $APEX_TRIGGERS triggers, $ACTIVE_FLOWS flows, $LWC_BUNDLES LWC, $CUSTOM_OBJECTS objects"

# ── Phase 2: Bulk metadata retrieval ───────────────────────────────────────

echo ""
echo "Phase 2: Retrieving Apex class source..."
sf project retrieve start -m ApexClass \
  --target-org "$TARGET_ORG" \
  --output-dir "$OUTPUT_DIR/intermediate/apex" \
  2>/dev/null || echo "  WARN: Apex class retrieval failed (may be empty)"

echo "Phase 3: Retrieving Apex trigger source..."
sf project retrieve start -m ApexTrigger \
  --target-org "$TARGET_ORG" \
  --output-dir "$OUTPUT_DIR/intermediate/triggers" \
  2>/dev/null || echo "  WARN: Apex trigger retrieval failed (may be empty)"

echo "Phase 4: Retrieving Flow definitions..."
sf project retrieve start -m Flow \
  --target-org "$TARGET_ORG" \
  --output-dir "$OUTPUT_DIR/intermediate/flows" \
  2>/dev/null || echo "  WARN: Flow retrieval failed (may be empty)"

echo "Phase 5: Retrieving LWC bundles..."
sf project retrieve start -m LightningComponentBundle \
  --target-org "$TARGET_ORG" \
  --output-dir "$OUTPUT_DIR/intermediate/lwc" \
  2>/dev/null || echo "  WARN: LWC retrieval failed (may be empty)"

# ── Phase 6: Detail queries (permissions, metadata) ───────────────────────

echo ""
echo "Phase 6: Querying detailed metadata..."

# Apex class metadata
query_tooling "SELECT Id, Name, LengthWithoutComments, ApiVersion FROM ApexClass WHERE NamespacePrefix = null ORDER BY Name" \
  "$RAW_DIR/apex_classes.json"

# Apex trigger metadata
query_tooling "SELECT Id, Name, TableEnumOrId, ApiVersion, Status FROM ApexTrigger WHERE NamespacePrefix = null ORDER BY Name" \
  "$RAW_DIR/apex_triggers.json"

# Flow definitions
query_tooling "SELECT Id, DeveloperName, MasterLabel, ActiveVersionId, ActiveVersion.VersionNumber, ActiveVersion.ProcessType FROM FlowDefinition WHERE ActiveVersionId != null AND NamespacePrefix = null ORDER BY DeveloperName" \
  "$RAW_DIR/flow_definitions.json"

# Active flow details (includes Process Builders)
query_tooling "SELECT Id, Definition.DeveloperName, ProcessType, Status, VersionNumber FROM Flow WHERE Status = 'Active' AND Definition.NamespacePrefix = null ORDER BY Definition.DeveloperName" \
  "$RAW_DIR/active_flows.json"

# LWC bundles
query_tooling "SELECT Id, DeveloperName, MasterLabel, ApiVersion FROM LightningComponentBundle WHERE NamespacePrefix = null ORDER BY DeveloperName" \
  "$RAW_DIR/lwc_bundles.json"

# Custom objects
query_tooling "SELECT Id, DeveloperName, Description FROM CustomObject WHERE NamespacePrefix = null ORDER BY DeveloperName" \
  "$RAW_DIR/custom_objects.json"

# Validation rules
query_tooling "SELECT Id, EntityDefinition.QualifiedApiName, ValidationName, Active, Description, ErrorMessage FROM ValidationRule WHERE NamespacePrefix = null ORDER BY EntityDefinition.QualifiedApiName" \
  "$RAW_DIR/validation_rules.json"

# Workflow rules (no Active field — it doesn't exist on WorkflowRule)
query_tooling "SELECT Id, Name, TableEnumOrId FROM WorkflowRule WHERE NamespacePrefix = null ORDER BY Name" \
  "$RAW_DIR/workflow_rules.json"

# Profiles
query_soql "SELECT Id, Name, UserType FROM Profile ORDER BY Name" \
  "$RAW_DIR/profiles.json"

# Permission sets (filtered: not profile-owned, not groups, no namespace)
query_soql "SELECT Id, Name, Label, Description FROM PermissionSet WHERE IsOwnedByProfile = false AND NamespacePrefix = null AND Type != 'Group' ORDER BY Name" \
  "$RAW_DIR/permission_sets.json"

# Permission set groups
query_soql "SELECT Id, DeveloperName, MasterLabel, Status, Description FROM PermissionSetGroup ORDER BY DeveloperName" \
  "$RAW_DIR/permission_set_groups.json"

# PSG components (hierarchy)
query_soql "SELECT PermissionSetGroupId, PermissionSetGroup.DeveloperName, PermissionSetId, PermissionSet.Name FROM PermissionSetGroupComponent ORDER BY PermissionSetGroup.DeveloperName" \
  "$RAW_DIR/psg_components.json"

# Permission set assignments
query_soql "SELECT PermissionSetId, PermissionSet.Name FROM PermissionSetAssignment WHERE PermissionSet.IsOwnedByProfile = false ORDER BY PermissionSet.Name" \
  "$RAW_DIR/ps_assignments.json"

# High-risk permissions
query_soql "SELECT Name, Label, PermissionsModifyAllData, PermissionsViewAllData, PermissionsManageUsers, PermissionsAuthorApex FROM PermissionSet WHERE IsOwnedByProfile = false AND (PermissionsModifyAllData = true OR PermissionsViewAllData = true OR PermissionsManageUsers = true OR PermissionsAuthorApex = true)" \
  "$RAW_DIR/high_risk_permissions.json"

# Record types
query_soql "SELECT Id, Name, SobjectType, IsActive, Description FROM RecordType ORDER BY SobjectType" \
  "$RAW_DIR/record_types.json"

# Custom fields (grouped by object for data model analysis)
query_tooling "SELECT Id, DeveloperName, TableEnumOrId, DataType, Description FROM CustomField WHERE NamespacePrefix = null ORDER BY TableEnumOrId, DeveloperName" \
  "$RAW_DIR/custom_fields.json"

# ── Done ────────────────────────────────────────────────────────────────────

echo ""
echo "=== Extraction complete ==="
echo "Raw query results:   $RAW_DIR/"
echo "Apex source:         $OUTPUT_DIR/intermediate/apex/"
echo "Trigger source:      $OUTPUT_DIR/intermediate/triggers/"
echo "Flow definitions:    $OUTPUT_DIR/intermediate/flows/"
echo "LWC bundles:         $OUTPUT_DIR/intermediate/lwc/"
echo ""
echo "Next: AI agent scores the extracted data, writes scored JSON, then runs:"
echo "  python scripts/generate_reports.py --input-dir $OUTPUT_DIR --output-dir $OUTPUT_DIR --org-name \"$ORG_NAME\""
