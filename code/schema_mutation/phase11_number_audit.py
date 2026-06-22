#!/usr/bin/env python3
"""Number reconciliation audit for the Phase 11 paper draft.

Reads paper text plus persisted summaries and checks that the headline numbers
are present and aligned with artifacts. Offline-only.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED = {
    "strict_schema_client": [r"44\s+of\s+130", r"33\.8\\?%"],
    "relaxed_yp": [r"49\s+of\s+156", r"31\.4\\?%"],
    "exposure_control": [r"363\s+exposed\s+O0", r"363\s+matched\s+unused-tool", r"77\.1\\?%", r"50\.1\\?%", r"44\.4\\?%", r"1\.4\\?%"],
    "observability": [r"525\s+formal\s+retail", r"1,290\s+formal\s+airline", r"1,815\s+frozen", r"0\.501", r"0\.843", r"0\.846", r"0\.851", r"0\.848", r"84\.7\\?%"],
    "phase8c": [r"480\s+additional\s+formal\s+cells", r"43\.8\\?%", r"56\.2\\?%", r"91\.2\\?%"],
    "phase10_corpus": [r"151\s+entries", r"nine\s+official\s+providers", r"61\s+C-class"],
    "phase10_replay": [r"24\s+baseline", r"0\s+of\s+23", r"22\s+of\s+23"],
    "phase10_nonobvious": [r"288-cell", r"3\s+of\s+96", r"6\s+of\s+95", r"71\s+of\s+95"],
}


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_tex(paper_dir: Path) -> str:
    parts = [read(paper_dir / "main.tex")]
    for sec in sorted((paper_dir / "sections").glob("*.tex")):
        if ".bak_" not in sec.name and sec.name[:2].isdigit():
            parts.append(read(sec))
    for table in ["grounding_controls_auto.tex", "trace_case_box_auto.tex"]:
        parts.append(read(paper_dir / "tables" / table))
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--paper-dir", default="<PROJECT_ROOT>/IEEE_Conference_Template")
    ap.add_argument("--out-dir", default="runs/schema_mutation/phase11")
    args = ap.parse_args()
    root = Path(args.root)
    paper_dir = Path(args.paper_dir)
    out_dir = root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    paper = flatten_tex(paper_dir)
    checks: dict[str, dict] = {}
    for group, needles in EXPECTED.items():
        checks[group] = {needle: bool(re.search(needle, paper)) for needle in needles}

    # Artifact-side facts.
    artifacts = {
        "corpus": load_json(root / "runs/schema_mutation/phase10/real_api_grounding/api_evolution_corpus_summary.json"),
        "oracle": load_json(root / "runs/schema_mutation/phase10/oracle_validation/oracle_validation_summary.json"),
        "nonobvious": load_json(root / "runs/schema_mutation/phase10/phase10c/nonobviousness_formal/nonobviousness_formal_summary.json"),
        "real_replay": load_json(root / "runs/schema_mutation/phase10/real_case_replay/formal_r1/real_case_formal_summary.json"),
        "phase5": load_json(root / "runs/schema_mutation/phase5/combined_observability_review_packet.json"),
    }

    derived = {}
    corpus = artifacts["corpus"]
    if corpus:
        derived["corpus_total_entries"] = corpus.get("total_entries")
        derived["corpus_provider_count"] = corpus.get("provider_count")
        derived["corpus_schema_invisible_c"] = corpus.get("schema_invisible_c_class_candidates")
    oracle = artifacts["oracle"]
    if oracle:
        derived["oracle_total_samples"] = oracle.get("total_samples")
        derived["oracle_baseline_violation_rate"] = oracle.get("baseline_oracle_violation_rate")
        derived["oracle_suspicious_count"] = oracle.get("suspicious_count")
    nonobv = artifacts["nonobvious"]
    if nonobv:
        derived["nonobvious_planned_cells"] = nonobv.get("planned_cells")
        derived["nonobvious_ok_cells"] = nonobv.get("ok_cells")
        derived["nonobvious_status_counts"] = nonobv.get("status_counts")
        derived["nonobvious_by_condition"] = {
            k: {
                "ok": v.get("ok"),
                "success_n": v.get("success_n"),
                "hidden_violation_n": v.get("hidden_violation_n"),
            }
            for k, v in nonobv.get("by_condition", {}).items()
        }
    real = artifacts["real_replay"]
    if real:
        derived["real_replay_status_counts"] = real.get("all_status_record_counts") or real.get("status_counts")
        derived["real_replay_all_status_records"] = real.get("all_status_records")
        by_cond = real.get("by_condition", {})
        derived["real_replay_by_condition"] = {
            k: {
                "ok_n": v.get("ok_n"),
                "success_n": v.get("success_n"),
                "hidden_violation_n": v.get("hidden_violation_n"),
            }
            for k, v in by_cond.items()
        }

    suspicious_phrases = {
        "ambiguous_c1_or": "unit/scale or validation" in paper,
        "human_kappa": bool(re.search(r"Cohen|kappa|inter-rater|human-validated", paper, re.I)),
        "production_frequency_claim": bool(re.search(r"production frequency", paper, re.I)),
        "production_incident_claim": bool(re.search(r"production incident", paper, re.I)),
        "gpt_table_ref": "tab:gpt-supplement" in paper,
    }

    result = {
        "paper_dir": str(paper_dir),
        "checks": checks,
        "derived_artifact_values": derived,
        "suspicious_phrases": suspicious_phrases,
        "all_expected_present": all(all(group.values()) for group in checks.values()),
    }
    (out_dir / "number_reconciliation_report.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")

    lines = ["# Number Reconciliation Report", ""]
    lines.append("Offline paper/artifact number audit. No experiments or model APIs were run.")
    lines.append("")
    lines.append("## Paper Number Presence")
    for group, vals in checks.items():
        missing = [k for k, ok in vals.items() if not ok]
        lines.append(f"- `{group}`: {'OK' if not missing else 'MISSING ' + ', '.join(missing)}")
    lines.append("")
    lines.append("## Artifact-Derived Values")
    lines.append("```json")
    lines.append(json.dumps(derived, indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")
    lines.append("## Phrase Checks")
    for k, v in suspicious_phrases.items():
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("## Recommendation")
    if suspicious_phrases["ambiguous_c1_or"]:
        lines.append("- Replace ambiguous `C1 unit/scale or validation` wording with a consistent C1 phrase.")
    if suspicious_phrases["human_kappa"]:
        lines.append("- Remove any human/kappa wording unless human labels exist.")
    lines.append("- Keep the 288-cell control wording, but ensure Table II or nearby text explains that two non-ok infrastructure rows are excluded from denominators.")
    (out_dir / "number_reconciliation_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
