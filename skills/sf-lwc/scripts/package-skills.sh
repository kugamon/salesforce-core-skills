#!/usr/bin/env bash
set -euo pipefail

# Package the Salesforce MCP server skills as standalone .skill files for distribution.
#
# Each .skill package contains:
#   SKILL.md      — the skill file with a License section appended
#   LICENSE       — MIT license (copied from parent plugin, falls back to repo root)
#   CREDITS.md    — attribution file (copied from parent plugin, if present)
#
# The .skill format is a zip archive with a .skill extension.
#
# Output: install/skills/<skill-name>.skill

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/install/skills"

rm -rf "$SKILLS_DIR"
mkdir -p "$SKILLS_DIR"

# Base license section appended to SKILL.md so each skill is self-contained.
# A CREDITS line is appended conditionally below if CREDITS.md is present.
LICENSE_SECTION_BASE='---

## License

MIT License — see [LICENSE](LICENSE) for details.
'

LICENSE_SECTION_CREDITS='
For credits and attribution see [CREDITS.md](CREDITS.md).'

echo "=== Packaging the Salesforce MCP server Skills ==="
echo ""

SKILL_COUNT=0

# Find all SKILL.md files at plugin/skills/skillname/SKILL.md
for skill_md in "$REPO_ROOT"/*/skills/*/SKILL.md; do
  [[ -f "$skill_md" ]] || continue

  skill_dir="$(dirname "$skill_md")"
  skill_name="$(basename "$skill_dir")"
  plugin_dir="$(dirname "$(dirname "$skill_dir")")"
  plugin_name="$(basename "$plugin_dir")"

  # Skip directories with spaces (e.g. "sf-apex 2") — likely artifacts
  if [[ "$plugin_name" == *" "* ]]; then
    echo "  Skipping '$plugin_name' (contains spaces, likely artifact)"
    continue
  fi

  echo "  Packaging skill: $skill_name..."

  tmp_dir="$(mktemp -d)"

  # SKILL.md — strip frontmatter keys not allowed in standalone skills,
  # then append License section.
  # Allowed keys: name, description, license, allowed-tools, compatibility, metadata
  # Stripped keys: hooks (requires plugin infrastructure; invalid standalone)
  python3 - "$skill_md" "$tmp_dir/SKILL.md" <<'PYEOF'
import sys

ALLOWED = {'name', 'description', 'license', 'allowed-tools', 'compatibility', 'metadata'}

src, dst = sys.argv[1], sys.argv[2]
content = open(src).read()

if content.startswith('---\n'):
    end = content.index('\n---\n', 4)
    frontmatter_lines = content[4:end].split('\n')
    body = content[end + 5:]

    out_lines = []
    skip = False
    for line in frontmatter_lines:
        # Top-level key: non-indented, non-empty
        if line and not line[0].isspace():
            key = line.split(':')[0].strip()
            skip = key not in ALLOWED
            if skip:
                continue  # don't warn, just drop silently
        if not skip:
            out_lines.append(line)

    new_fm = '\n'.join(out_lines).strip()
    content = f'---\n{new_fm}\n---\n\n{body}'

open(dst, 'w').write(content)
PYEOF
  # LICENSE — prefer plugin-level copy, fall back to repo root
  if [[ -f "$plugin_dir/LICENSE" ]]; then
    cp "$plugin_dir/LICENSE" "$tmp_dir/LICENSE"
  elif [[ -f "$REPO_ROOT/LICENSE" ]]; then
    cp "$REPO_ROOT/LICENSE" "$tmp_dir/LICENSE"
  fi

  # CREDITS.md — only present in some plugins; append reference only if present
  if [[ -f "$plugin_dir/CREDITS.md" ]]; then
    cp "$plugin_dir/CREDITS.md" "$tmp_dir/CREDITS.md"
    printf '\n%s%s\n' "$LICENSE_SECTION_BASE" "$LICENSE_SECTION_CREDITS" >> "$tmp_dir/SKILL.md"
  else
    printf '\n%s\n' "$LICENSE_SECTION_BASE" >> "$tmp_dir/SKILL.md"
  fi

  # Package contents as .skill file (zip archive with .skill extension)
  (cd "$tmp_dir" && zip -r -q "$SKILLS_DIR/${skill_name}.skill" .)

  rm -rf "$tmp_dir"
  SKILL_COUNT=$((SKILL_COUNT + 1))
done

echo ""
echo "  Packaged $SKILL_COUNT skills"
echo ""
echo "=== Done ==="
echo ""
echo "Output in $SKILLS_DIR/:"
ls -lh "$SKILLS_DIR"/*.skill 2>/dev/null || echo "  (none)"
