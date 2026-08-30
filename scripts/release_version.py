#!/usr/bin/env python3
"""
Decide the next release from Conventional Commits, bump the manifests, and
emit release notes.

Used by .github/workflows/release.yml, but designed to be runnable (and
testable) locally:

    python3 scripts/release_version.py --dry-run          # what would happen
    python3 scripts/release_version.py --self-test        # logic tests, no I/O

Bump rules (Conventional Commits):
    ! or BREAKING CHANGE  -> major
    feat                  -> minor
    fix | perf | refactor -> patch
    docs | chore | ci | style | test | build | revert -> no release on their own

The "no release on their own" rule is the point of skill-scoped automation:
a docs-only or CI-only merge shouldn't mint a version nobody needs.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFESTS = [
    ROOT / ".claude-plugin" / "marketplace.json",
    ROOT / "plugins" / "salesforce-core" / ".claude-plugin" / "plugin.json",
]
CHANGELOG = ROOT / "CHANGELOG.md"
REPO = "kugamon/salesforce-core-skills"

BUMP_NONE, BUMP_PATCH, BUMP_MINOR, BUMP_MAJOR = 0, 1, 2, 3
PATCH_TYPES = {"fix", "perf", "refactor"}
SECTIONS = [
    ("feat", "Features"),
    ("fix", "Fixes"),
    ("perf", "Performance"),
    ("refactor", "Internal"),
    ("docs", "Documentation"),
]
COMMIT_RE = re.compile(
    r"^(?P<type>build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)"
    r"(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<desc>.+)$"
)


def sh(*args: str) -> str:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()


def current_version() -> str:
    return json.loads(MANIFESTS[1].read_text())["version"]


def classify(subject: str, body: str = ""):
    """Return (bump level, parsed commit) for one commit."""
    m = COMMIT_RE.match(subject.strip())
    if not m:
        return BUMP_NONE, None
    parsed = m.groupdict()
    if parsed["bang"] or "BREAKING CHANGE" in body:
        return BUMP_MAJOR, parsed
    if parsed["type"] == "feat":
        return BUMP_MINOR, parsed
    if parsed["type"] in PATCH_TYPES:
        return BUMP_PATCH, parsed
    return BUMP_NONE, parsed


def next_version(version: str, bump: int) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if bump == BUMP_MAJOR:
        return f"{major + 1}.0.0"
    if bump == BUMP_MINOR:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def collect(since_tag):
    """[(subject, body)] since the tag (or the last 50 commits if untagged)."""
    rng = f"{since_tag}..HEAD" if since_tag else "-50"
    raw = sh("git", "log", rng, "--no-merges", "--format=%s%x1f%b%x1e")
    out = []
    for chunk in (c for c in raw.split("\x1e") if c.strip()):
        subject, _, body = chunk.partition("\x1f")
        out.append((subject.strip(), body.strip()))
    return out


def last_tag():
    tag = sh("git", "describe", "--tags", "--abbrev=0")
    return tag or None


def notes(commits, old: str, new: str) -> str:
    buckets = {}
    for subject, body in commits:
        _, parsed = classify(subject, body)
        if not parsed or parsed["type"] in {"chore", "ci", "style", "test", "build", "revert"}:
            continue
        scope = f"**{parsed['scope']}** — " if parsed["scope"] else ""
        breaking = "**BREAKING** " if parsed["bang"] or "BREAKING CHANGE" in body else ""
        buckets.setdefault(parsed["type"], []).append(f"- {breaking}{scope}{parsed['desc']}")

    lines = []
    for key, title in SECTIONS:
        if buckets.get(key):
            lines.append(f"### {title}\n")
            lines.extend(buckets[key])
            lines.append("")
    if not lines:
        lines = ["Maintenance release.", ""]
    lines.append(f"**Full diff:** https://github.com/{REPO}/compare/v{old}...v{new}")
    return "\n".join(lines)


def write_manifests(new: str) -> None:
    for path in MANIFESTS:
        data = json.loads(path.read_text())
        node = data["plugins"][0] if "plugins" in data else data
        node["version"] = new
        path.write_text(json.dumps(data, indent=2) + "\n")


def write_changelog(new: str, body: str) -> None:
    if not CHANGELOG.exists():
        return
    from datetime import date

    text = CHANGELOG.read_text()
    summary = " ".join(
        line[2:] for line in body.splitlines() if line.startswith("- ")
    )[:400]
    entry = f"## [{new}] — {date.today().isoformat()}\n- {summary}\n\n"
    anchor = "\n## ["
    idx = text.find(anchor)
    text = (text[: idx + 1] + entry + text[idx + 1 :]) if idx != -1 else text + "\n" + entry
    CHANGELOG.write_text(text)


def self_test() -> int:
    cases = [
        ("feat(sf-orgdiff): add package comparison", "", BUMP_MINOR),
        ("fix(sf-apex): stop scoring managed bodies", "", BUMP_PATCH),
        ("perf: batch inventory queries", "", BUMP_PATCH),
        ("refactor(shared): extract handler base", "", BUMP_PATCH),
        ("docs: clarify headless rules", "", BUMP_NONE),
        ("chore(deps): bump action", "", BUMP_NONE),
        ("ci: add PR title check", "", BUMP_NONE),
        ("feat!: drop API v59 support", "", BUMP_MAJOR),
        ("fix: adjust guard", "BREAKING CHANGE: hook output shape changed", BUMP_MAJOR),
        ("Update README", "", BUMP_NONE),
        ("chore(release): v2.1.0 [skip ci]", "", BUMP_NONE),
    ]
    failures = 0
    for subject, body, expected in cases:
        got, _ = classify(subject, body)
        if got != expected:
            print(f"  FAIL {subject!r}: expected {expected}, got {got}")
            failures += 1
    versions = [
        ("2.1.0", BUMP_PATCH, "2.1.1"),
        ("2.1.0", BUMP_MINOR, "2.2.0"),
        ("2.1.0", BUMP_MAJOR, "3.0.0"),
        ("2.1.9", BUMP_PATCH, "2.1.10"),
    ]
    for old, bump, expected in versions:
        got = next_version(old, bump)
        if got != expected:
            print(f"  FAIL {old} +{bump}: expected {expected}, got {got}")
            failures += 1
    agg = max(classify(s, b)[0] for s, b in [("docs: x", ""), ("fix: y", ""), ("feat: z", "")])
    if agg != BUMP_MINOR:
        print(f"  FAIL aggregate: expected {BUMP_MINOR}, got {agg}")
        failures += 1
    print("self-test:", "PASS" if not failures else f"{failures} FAILURES")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the decision, write nothing")
    ap.add_argument("--self-test", action="store_true", help="run logic tests only")
    ap.add_argument("--github-output", help="path to write key=value outputs (GitHub Actions)")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    old = current_version()
    tag = last_tag()
    commits = collect(tag)
    bump = max((classify(s, b)[0] for s, b in commits), default=BUMP_NONE)

    if bump == BUMP_NONE:
        print(f"No releasable commits since {tag or 'start'} ({len(commits)} scanned) - skipping.")
        if args.github_output:
            Path(args.github_output).write_text("released=false\n")
        return 0

    new = next_version(old, bump)
    body = notes(commits, old, new)
    level = {BUMP_PATCH: "patch", BUMP_MINOR: "minor", BUMP_MAJOR: "major"}[bump]
    print(f"{old} -> {new} ({level}, {len(commits)} commits since {tag or 'start'})\n")
    print(body)

    if args.dry_run:
        print("\n[dry run] no files written")
        return 0

    write_manifests(new)
    write_changelog(new, body)
    if args.github_output:
        out = Path(args.github_output)
        delim = "EOF_NOTES"
        out.write_text(
            f"released=true\nversion={new}\nlevel={level}\nnotes<<{delim}\n{body}\n{delim}\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
