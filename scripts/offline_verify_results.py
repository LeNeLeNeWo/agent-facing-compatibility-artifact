#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def verify_main():
    headlines = load_json("docs/reproduction_headlines.json")
    assert_equal(headlines["phase5_formal_cells"]["total"], 1815, "formal total")
    assert_equal(headlines["phase5_formal_cells"]["retail"], 525, "retail formal cells")
    assert_equal(headlines["phase5_formal_cells"]["airline"], 1290, "airline formal cells")
    assert_equal(headlines["phase8_exposure_control"]["exposed_o0_n"], 363, "exposed O0 N")
    assert_equal(headlines["phase8_exposure_control"]["unused_control_n"], 363, "unused-control N")
    nr = load_json("results/phase11_audits/number_reconciliation_report.json")
    assert nr["all_expected_present"] is True


def verify_phase10():
    corpus = load_json("data/real_api_grounding/api_evolution_corpus_summary.json")
    assert_equal(corpus["total_entries"], 151, "public API entries")
    assert_equal(corpus["schema_invisible_c_class_candidates"], 61, "C-class candidates")
    nonobv = load_json("results/phase10_nonobviousness/nonobviousness_analysis_report.json")
    by_cond = nonobv.get("condition_summary") or nonobv.get("condition_results")
    assert_equal(by_cond["O0_increased_reasoning_budget"]["success_n"], 3, "nonobvious reasoning success")
    assert_equal(by_cond["O0_reflection_scaffold"]["success_n"], 6, "nonobvious reflection success")
    assert_equal(by_cond["rule_in_tool_preamble_upper_bound"]["success_n"], 71, "nonobvious visible success")
    replay = load_json("results/phase10_real_case_replay/real_case_formal_summary.json")
    assert_equal(replay["by_condition"]["baseline_old_api"]["success_n"], 24, "real replay baseline")
    assert_equal(replay["by_condition"]["evolved_o0_silent"]["success_n"], 0, "real replay silent")
    assert_equal(replay["by_condition"]["evolved_visible_feedback"]["success_n"], 22, "real replay visible")


def verify_figures():
    required = [
        "figures/pdf/combined_observability_gradient_curve.pdf",
        "figures/pdf/combined_observability_uplift_forest.pdf",
        "figures/pdf/exposure_control_contrast.pdf",
        "figures/pdf/c_semantic_generalization.pdf",
        "figures/pdf/nonobviousness_control.pdf",
        "figures/pdf/real_case_replay.pdf",
    ]
    for rel in required:
        p = ROOT / rel
        if not p.exists() or p.stat().st_size <= 0:
            raise AssertionError(f"missing or empty figure: {rel}")


def verify_audits():
    for rel in [
        "results/phase11_audits/cluster_stats_audit.json",
        "results/phase11_audits/number_reconciliation_report.json",
        "results/phase10_nonobviousness/integrity_audit.json",
        "docs/artifact_manifest.json",
    ]:
        p = ROOT / rel
        if not p.exists() or p.stat().st_size <= 0:
            raise AssertionError(f"missing audit artifact: {rel}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=["all", "main", "phase10", "figures", "audits"], default="all")
    args = ap.parse_args()
    if args.section in {"all", "main"}:
        verify_main()
    if args.section in {"all", "phase10"}:
        verify_phase10()
    if args.section in {"all", "figures"}:
        verify_figures()
    if args.section in {"all", "audits"}:
        verify_audits()
    report = {"section": args.section, "status": "ok"}
    out = ROOT / "docs" / "offline_reproduction_report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
