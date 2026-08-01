#!/usr/bin/env python3
"""Structural validation for salesforce-core-skills. Run from repo root."""
import json, re, sys, io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "plugins" / "salesforce-core" / "skills"
errors = []

def err(msg): errors.append(msg)

# Manifests parse and agree
try:
    mp = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
    pj = json.loads((ROOT / "plugins" / "salesforce-core" / ".claude-plugin" / "plugin.json").read_text())
    if mp["plugins"][0]["version"] != pj["version"]:
        err(f"version mismatch: marketplace {mp['plugins'][0]['version']} vs plugin {pj['version']}")
    src = ROOT / mp["plugins"][0]["source"].lstrip("./")
    if not (src / ".claude-plugin" / "plugin.json").exists():
        err(f"marketplace source path invalid: {mp['plugins'][0]['source']}")
except Exception as e:
    err(f"manifest error: {e}")

# Every skill: SKILL.md with frontmatter (name matches dir, description), README, LICENSE
fm_re = re.compile(r"^---\n(.*?)\n---", re.S)
skill_dirs = sorted(d for d in SKILLS.iterdir() if d.is_dir())
if len(skill_dirs) < 13:
    err(f"expected >=13 skills, found {len(skill_dirs)}")
for d in skill_dirs:
    sm = d / "SKILL.md"
    if not sm.exists():
        err(f"{d.name}: missing SKILL.md"); continue
    text = sm.read_text(encoding="utf-8", errors="replace")
    m = fm_re.match(text)
    if not m:
        err(f"{d.name}: SKILL.md missing frontmatter"); continue
    fm = m.group(1)
    nm = re.search(r"^name:\s*[\"']?([\w-]+)", fm, re.M)
    if not nm or nm.group(1) != d.name:
        err(f"{d.name}: frontmatter name {'missing' if not nm else nm.group(1)!r} != dir name")
    if "description:" not in fm:
        err(f"{d.name}: frontmatter missing description")
    for req in ("README.md", "LICENSE"):
        if not (d / req).exists():
            err(f"{d.name}: missing {req}")
    # broken local reference paths mentioned in SKILL.md tables
    for ref in re.findall(r"`references/([\w./-]+)`", text):
        if not (d / "references" / ref).exists():
            err(f"{d.name}: SKILL.md references missing file references/{ref}")

# No vendor strings outside LICENSE notices
for f in ROOT.rglob("*"):
    if f.is_file() and f.suffix in {".md", ".py", ".json"} and f.name not in ("LICENSE", "validate_skills.py") and ".git" not in f.parts:
        if re.search(r"cirra", f.read_text(encoding="utf-8", errors="replace"), re.I):
            err(f"vendor string in {f.relative_to(ROOT)}")

# evals file parses and covers every skill
try:
    ev = json.loads((ROOT / "evals" / "evals.json").read_text())
    covered = {e["skill"] for e in ev["evals"]}
    missing = {d.name for d in skill_dirs} - covered
    if missing:
        err(f"evals.json missing prompts for: {sorted(missing)}")
except Exception as e:
    err(f"evals error: {e}")

if errors:
    print(f"FAIL — {len(errors)} problem(s):")
    for e in errors: print(f"  - {e}")
    sys.exit(1)
print(f"OK — {len(skill_dirs)} skills validated, manifests consistent, evals cover all skills")
