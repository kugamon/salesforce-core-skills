#!/usr/bin/env python3
"""
Pre-scoring orchestrator for Salesforce org audits.

Walks the intermediate directory produced by Phase C body fetching,
runs the appropriate static-analysis validator on each file, and
produces the JSON score files that generate_reports.py expects.

Usage:
    python pre_score.py \\
      --intermediate-dir ./audit_output/intermediate \\
      --output-dir ./audit_output \\
      [--threshold 70]

Validators invoked:
    - validate_apex.py   (ApexValidator)      → apex_scores.json
    - validate_flow.py   (EnhancedFlowValidator) → flow_scores.json
    - validate_slds.py   (SLDSValidator)      → lwc_scores.json

Components scoring below --threshold (percentage of max) are flagged
in pre_score_summary.json for LLM review.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Dynamic module loading
# ---------------------------------------------------------------------------

SKILLS_ROOT = Path(__file__).resolve().parent.parent.parent  # skills/


def _load_module(rel_path: str):
    """Import a Python module from *rel_path* (relative to skills/ dir)."""
    path = SKILLS_ROOT / rel_path
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    # Some validators insert their own dir onto sys.path; make sure that
    # works even when loaded from here.
    original_path = list(sys.path)
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path = original_path
    return module


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------


def _score_apex_files(apex_dir: Path, trigger_dir: Path, threshold_pct: int):
    """Score .cls and .trigger files with the Apex validator."""
    mod = _load_module("sf-apex/scripts/validate_apex.py")
    if mod is None:
        return [], [], []

    apex_scores = []
    trigger_findings = []
    needs_review = []

    for directory, is_trigger in [(apex_dir, False), (trigger_dir, True)]:
        if not directory.is_dir():
            continue
        ext = "*.trigger" if is_trigger else "*.cls"
        for fp in sorted(directory.glob(ext)):
            try:
                result = mod.ApexValidator(str(fp)).validate()
            except Exception as exc:
                result = {
                    "file": fp.name,
                    "score": 0,
                    "max_score": 150,
                    "issues": [
                        {"message": f"Validator error: {exc}", "severity": "CRITICAL"}
                    ],
                }

            name = fp.stem
            score = result.get("score", 0)
            max_score = result.get("max_score", 150)
            issues = [
                i.get("message", str(i)) if isinstance(i, dict) else str(i)
                for i in result.get("issues", [])
            ]

            if is_trigger:
                # Preserve original severity from validator; default MEDIUM.
                raw_issues = result.get("issues", [])
                findings = []
                for ri in raw_issues:
                    if isinstance(ri, dict):
                        findings.append(
                            {
                                "severity": ri.get("severity", "MEDIUM"),
                                "message": ri.get("message", str(ri)),
                            }
                        )
                    else:
                        findings.append({"severity": "MEDIUM", "message": str(ri)})
                trigger_findings.append(
                    {
                        "name": name,
                        "object": "",
                        "events": "",
                        "score": score,
                        "max_score": max_score,
                        "findings": findings,
                    }
                )
            else:
                apex_scores.append(
                    {
                        "name": name,
                        "score": score,
                        "max_score": max_score,
                        "issues": issues,
                    }
                )

            pct = (score / max_score * 100) if max_score else 0
            if pct < threshold_pct:
                needs_review.append(
                    {
                        "name": name,
                        "domain": "triggers" if is_trigger else "apex",
                        "score": score,
                        "max_score": max_score,
                        "pct": round(pct, 1),
                        "reason": f"Below {threshold_pct}% threshold",
                    }
                )

    return apex_scores, trigger_findings, needs_review


def _score_flow_files(flows_dir: Path, threshold_pct: int):
    """Score .flow-meta.xml files with the Flow validator."""
    mod = _load_module("sf-flow/scripts/validate_flow.py")
    if mod is None:
        return [], []

    flow_scores = []
    needs_review = []

    if not flows_dir.is_dir():
        return flow_scores, needs_review

    for fp in sorted(flows_dir.glob("*.flow-meta.xml")):
        try:
            result = mod.EnhancedFlowValidator(str(fp)).validate()
        except Exception as exc:
            result = {
                "flow_name": fp.stem.removesuffix(".flow-meta"),
                "overall_score": 0,
                "critical_issues": [{"message": f"Validator error: {exc}"}],
                "warnings": [],
            }

        name = result.get("flow_name", fp.stem.removesuffix(".flow-meta"))
        score = result.get("overall_score", 0)
        max_score = 110
        issues = [
            ci.get("message", str(ci)) if isinstance(ci, dict) else str(ci)
            for ci in result.get("critical_issues", [])
        ] + [
            w.get("message", str(w)) if isinstance(w, dict) else str(w)
            for w in result.get("warnings", [])
        ]

        flow_scores.append(
            {
                "name": name,
                "process_type": "",
                "score": score,
                "max_score": max_score,
                "issues": issues,
            }
        )

        pct = (score / max_score * 100) if max_score else 0
        if pct < threshold_pct:
            needs_review.append(
                {
                    "name": name,
                    "domain": "flows",
                    "score": score,
                    "max_score": max_score,
                    "pct": round(pct, 1),
                    "reason": f"Below {threshold_pct}% threshold",
                }
            )

    return flow_scores, needs_review


def _score_lwc_bundles(lwc_dir: Path, threshold_pct: int):
    """Score LWC bundles by validating each file and aggregating per bundle."""
    mod = _load_module("sf-lwc/scripts/validate_slds.py")
    if mod is None:
        return [], []

    lwc_scores = []
    needs_review = []

    if not lwc_dir.is_dir():
        return lwc_scores, needs_review

    for bundle_dir in sorted(lwc_dir.iterdir()):
        if not bundle_dir.is_dir():
            continue

        # Validate each file in the bundle; average per-file scores.
        all_issues = []
        max_score = 165
        file_scores = []

        for ext in ("*.html", "*.css", "*.js"):
            for fp in bundle_dir.glob(ext):
                try:
                    result = mod.SLDSValidator(str(fp)).validate()
                except Exception as exc:
                    result = {
                        "score": 0,
                        "max_score": max_score,
                        "issues": [
                            {
                                "message": f"Validator error: {exc}",
                                "severity": "CRITICAL",
                            }
                        ],
                    }

                file_scores.append(result.get("score", 0))

                for issue in result.get("issues", []):
                    msg = (
                        issue.get("message", str(issue))
                        if isinstance(issue, dict)
                        else str(issue)
                    )
                    all_issues.append(msg)

        # Average per-file scores so bundles with multiple files aren't
        # penalized more than single-file components.  Bundles with no
        # scoreable files (no .html/.css/.js) get 0 so they are flagged.
        score = (
            round(sum(file_scores) / len(file_scores)) if file_scores else 0
        )
        name = bundle_dir.name

        lwc_scores.append(
            {
                "name": name,
                "score": score,
                "max_score": max_score,
                "issues": all_issues,
            }
        )

        pct = (score / max_score * 100) if max_score else 0
        if pct < threshold_pct:
            needs_review.append(
                {
                    "name": name,
                    "domain": "lwc",
                    "score": score,
                    "max_score": max_score,
                    "pct": round(pct, 1),
                    "reason": f"Below {threshold_pct}% threshold",
                }
            )

    return lwc_scores, needs_review


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def pre_score(intermediate_dir: Path, output_dir: Path, threshold_pct: int = 70):
    """Run all validators and write JSON score files.

    Returns a summary dict suitable for pre_score_summary.json.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Apex ---
    apex_scores, trigger_findings, apex_review = _score_apex_files(
        intermediate_dir / "apex",
        intermediate_dir / "triggers",
        threshold_pct,
    )

    # --- Flows ---
    flow_scores, flow_review = _score_flow_files(
        intermediate_dir / "flows",
        threshold_pct,
    )

    # --- LWC ---
    lwc_scores, lwc_review = _score_lwc_bundles(
        intermediate_dir / "lwc",
        threshold_pct,
    )

    # --- Write JSON score files ---
    for filename, data in [
        ("apex_scores.json", apex_scores),
        ("trigger_findings.json", trigger_findings),
        ("flow_scores.json", flow_scores),
        ("lwc_scores.json", lwc_scores),
    ]:
        (output_dir / filename).write_text(json.dumps(data, indent=2))

    # --- Build summary ---
    needs_review = apex_review + flow_review + lwc_review

    summary = {
        "threshold_pct": threshold_pct,
        "apex": {
            "scored": len(apex_scores),
            "below_threshold": len(
                [r for r in apex_review if r["domain"] == "apex"]
            ),
        },
        "triggers": {
            "scored": len(trigger_findings),
            "below_threshold": len(
                [r for r in apex_review if r["domain"] == "triggers"]
            ),
        },
        "flows": {
            "scored": len(flow_scores),
            "below_threshold": len(flow_review),
        },
        "lwc": {
            "scored": len(lwc_scores),
            "below_threshold": len(lwc_review),
        },
        "needs_llm_review": needs_review,
    }

    (output_dir / "pre_score_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Pre-score Salesforce components for org audit"
    )
    parser.add_argument(
        "--intermediate-dir",
        required=True,
        help="Path to intermediate directory with fetched bodies",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Path to write JSON score files",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=70,
        help="Percentage threshold below which components need LLM review (default: 70)",
    )
    args = parser.parse_args()

    summary = pre_score(
        Path(args.intermediate_dir),
        Path(args.output_dir),
        args.threshold,
    )

    # Print human-readable summary
    print("Pre-scoring complete:")
    for domain in ("apex", "triggers", "flows", "lwc"):
        info = summary[domain]
        flagged = info["below_threshold"]
        total = info["scored"]
        flag_str = f", {flagged} need LLM review" if flagged else ""
        print(f"  {domain:10s}: {total} scored{flag_str}")
    print(f"\nThreshold: {summary['threshold_pct']}% of max score")
    print(f"JSON scores written to: {args.output_dir}")


if __name__ == "__main__":
    main()
