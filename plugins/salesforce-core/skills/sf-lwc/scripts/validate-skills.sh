#!/usr/bin/env bash
# Validate agent skill directories using skills-ref.
#
# Usage:
#   scripts/validate-skills.sh           # validate all skills
#   scripts/validate-skills.sh --staged  # validate only skills with staged changes (pre-commit)

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
SKILLS_REF_PKG="git+https://github.com/agentskills/agentskills.git#subdirectory=skills-ref"
MIN_PYTHON_MINOR=11  # skills-ref requires Python >= 3.11
STAGED_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --staged) STAGED_ONLY=1 ;;
    *) echo "unknown argument: $arg" >&2; exit 1 ;;
  esac
done

# ── Check Python version ─────────────────────────────────────────────────────

if ! command -v python3 &>/dev/null; then
  echo "error: python3 is required (>= 3.${MIN_PYTHON_MINOR}) but not found" >&2
  echo "  Install from https://python.org or via your package manager" >&2
  exit 1
fi

python_minor=$(python3 -c 'import sys; print(sys.version_info.minor)')
python_major=$(python3 -c 'import sys; print(sys.version_info.major)')

if [[ $python_major -lt 3 || ($python_major -eq 3 && $python_minor -lt $MIN_PYTHON_MINOR) ]]; then
  python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  echo "error: python3 >= 3.${MIN_PYTHON_MINOR} required, found ${python_version}" >&2
  exit 1
fi

# ── Locate or install skills-ref ─────────────────────────────────────────────

find_skills_ref() {
  if command -v skills-ref &>/dev/null; then
    command -v skills-ref
    return 0
  fi
  if [[ -x "$REPO_ROOT/.venv/bin/skills-ref" ]]; then
    echo "$REPO_ROOT/.venv/bin/skills-ref"
    return 0
  fi
  return 1
}

install_skills_ref() {
  echo "skills-ref not found — installing into .venv ..."

  if command -v uv &>/dev/null; then
    if uv tool install "$SKILLS_REF_PKG" &>/dev/null; then
      if command -v skills-ref &>/dev/null; then
        command -v skills-ref; return 0
      fi
    fi
  fi

  [[ -x "$REPO_ROOT/.venv/bin/python" ]] || python3 -m venv "$REPO_ROOT/.venv"
  "$REPO_ROOT/.venv/bin/pip" install --quiet "$SKILLS_REF_PKG" || {
    echo "error: could not install skills-ref" >&2
    echo "  python3 -m venv .venv && .venv/bin/pip install '$SKILLS_REF_PKG'" >&2
    return 1
  }
  echo "$REPO_ROOT/.venv/bin/skills-ref"
}

SKILLS_REF="$(find_skills_ref || install_skills_ref)" || exit 1

# ── Find skill directories ────────────────────────────────────────────────────

# All skill dirs: parent of every SKILL.md matching */skills/*/SKILL.md
all_skill_dirs=()
while IFS= read -r skill_md; do
  all_skill_dirs+=("$(dirname "$skill_md")")
done < <(find "$REPO_ROOT" -path "*/.git" -prune -o -path "*/skills/*/SKILL.md" -print | sort)

if [[ $STAGED_ONLY -eq 1 ]]; then
  # Only validate dirs that contain staged files
  skill_dirs=()
  while IFS= read -r staged_file; do
    staged_path="$REPO_ROOT/$staged_file"
    for dir in "${all_skill_dirs[@]}"; do
      if [[ "$staged_path" == "$dir"/* || "$staged_path" == "$dir" ]]; then
        skill_dirs+=("$dir")
        break
      fi
    done
  done < <(git diff --cached --name-only)
  # Deduplicate
  if [[ ${#skill_dirs[@]} -gt 0 ]]; then
    IFS=$'\n' read -r -d '' -a skill_dirs < <(printf '%s\n' "${skill_dirs[@]}" | sort -u && printf '\0') || true
  fi
else
  skill_dirs=("${all_skill_dirs[@]}")
fi

[[ ${#skill_dirs[@]} -eq 0 ]] && exit 0

# ── Validate ─────────────────────────────────────────────────────────────────

errors=0
for dir in "${skill_dirs[@]}"; do
  rel="${dir#"$REPO_ROOT"/}"
  output=$("$SKILLS_REF" validate "$dir" 2>&1)
  rc=$?

  if [[ $rc -eq 0 ]]; then
    echo "✓  $rel"
    continue
  fi

  # Filter known false-positive: 'hooks' is a plugin frontmatter extension
  # not in the agentskills spec. Error format: "  - Unexpected fields in frontmatter: hooks. Only ..."
  real_errors=$(printf '%s\n' "$output" | grep "^  - " | grep -v "Unexpected fields in frontmatter: hooks\.")

  if [[ -z "$real_errors" ]]; then
    echo "✓  $rel"
  else
    echo "✗  $rel"
    printf '%s\n' "$real_errors" | sed 's/^  - /   /'
    errors=$((errors + 1))
  fi
done

exit $errors
