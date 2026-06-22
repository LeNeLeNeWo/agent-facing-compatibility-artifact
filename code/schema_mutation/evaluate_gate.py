"""Evaluate Semantic Compatibility Gate methods on existing artifacts.

This script produces Phase 2 artifacts without running expensive APIs. Existing
paired JSONL files are treated as cached replay evidence. The evaluator uses
final rewards only as labels for metrics, not as gate prediction features.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from code.schema_mutation.gate_policies import (  # noqa: E402
    GATE_METHODS,
    decision_is_positive,
)
from code.schema_mutation.semantic_compat_gate import (  # noqa: E402
    GateConfig,
    normalize_cell,
    parse_budget,
    run_gate,
)

RUNS = _REPO_ROOT / "runs" / "schema_mutation"
PAPER = _REPO_ROOT / "IEEE_Conference_Template"

DEFAULT_PAIRED_ARTIFACTS = [
    RUNS / "paired_day10_c4a_c4b_deepseek.jsonl",
    RUNS / "paired_day11_c4a_c4b_qwen_kimi.jsonl",
    RUNS / "paired_day16_airline_deepseek_s0_unused_control.jsonl",
    RUNS / "paired_day16_airline_deepseek_s12_c4a_c4b.jsonl",
    RUNS / "paired_day16_airline_qwen_max_c4a_c4b.jsonl",
]

PHASE5_OBSERVABILITY_PATTERNS = [
    "phase5/status/observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl",
    "phase5/status/airline_observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl",
]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"[warn] {path}:{line_no}: {exc}")
    return rows


def _is_phase5_status_path(path: Path) -> bool:
    return path.parent.name == "status" and "observability_from_baseline" in path.name


def _latest_by_cell_key(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    latest: dict[str, tuple[tuple[str, int], dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        key = row.get("cell_key")
        if not key:
            passthrough.append(row)
            continue
        time_key = str(row.get("started_at") or row.get("completed_at") or row.get("timestamp") or "")
        order_key = (time_key, idx)
        if key not in latest or order_key >= latest[key][0]:
            latest[key] = (order_key, row)
    deduped = passthrough + [item[1] for item in latest.values()]
    return deduped, max(0, len(rows) - len(deduped))


def _from_phase5_status(row: dict[str, Any], path: Path) -> dict[str, Any] | None:
    """Convert final Phase 5 status rows into paired replay-cache evidence.

    Gate policies may consume replayed semantic-oracle outcomes only when a
    method actually selects a cell. Final reward remains an evaluation label.
    Smoke, failed provider attempts, WYZ partial rows, and baseline-unsuccessful
    cells are excluded before normalization.
    """

    source = path.name.lower()
    if "smoke" in source or "retry_provider_error" in source:
        return None
    if row.get("fake_run"):
        return None
    if row.get("status") != "ok" or row.get("timeout"):
        return None
    if str(row.get("provider", "")).lower() == "wyzlab" or "wyz" in str(row.get("model", "")).lower():
        return None
    if row.get("baseline_success") is not True:
        return None
    obs = row.get("observability_level")
    if obs not in {"O0_silent", "O1_generic_error", "O2_policy_error", "O3_structured_policy_error", "O4_migration_note"}:
        return None
    reward = row.get("reward")
    if reward is None:
        reward = 1.0 if row.get("mutation_success") else 0.0
    return {
        "env": row.get("env"),
        "model": row.get("model"),
        "task_id": row.get("task_id"),
        "seed": row.get("seed", 0),
        "mutation_type": row.get("mutation_name") or "C4_business_rule_drift",
        "target_tool": row.get("target_tool"),
        "mutation_tool": row.get("target_tool"),
        "target_policy": row.get("protocol") or "intent_aligned",
        "runtime_policy_action": row.get("target_tool") if row.get("target_tool_called", True) else None,
        "observability_level": obs,
        "c4_runtime_mode": row.get("condition") or obs,
        "baseline_reward": 1.0,
        "mutation_reward": reward,
        "final_reward": reward,
        "oracle_rule_violation": bool(row.get("oracle_rule_violation")),
        "hidden_business_rule_violation": bool(row.get("hidden_business_rule_violation")),
        "visible_policy_error": bool(row.get("visible_policy_error")),
        "generic_error_visible": bool(row.get("generic_error_visible")),
        "structured_policy_error_visible": bool(row.get("structured_policy_error_visible")),
        "migration_note_visible": bool(row.get("migration_note_visible")),
        "failure_mode": row.get("failure_mode"),
        "cell_key": row.get("cell_key"),
    }


def _load_cells(paths: list[Path], include_fake: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    cells: list[dict[str, Any]] = []
    warnings: list[str] = []
    for path in paths:
        rows = _read_jsonl(path)
        if not rows:
            warnings.append(f"missing_or_empty: {path}")
            continue
        if _is_phase5_status_path(path):
            rows, duplicate_count = _latest_by_cell_key(rows)
            if duplicate_count:
                warnings.append(f"deduped_phase5_retry_rows: {path} ({duplicate_count})")
        paired_like = 0
        for r in rows:
            if _is_phase5_status_path(path):
                r = _from_phase5_status(r, path) or {}
                if not r:
                    continue
            if r.get("fake_run") and not include_fake:
                continue
            if "baseline_reward" not in r or "mutation_reward" not in r:
                continue
            paired_like += 1
            cells.append(normalize_cell(r, source=str(path)))
        if paired_like == 0:
            warnings.append(f"no_paired_rows_with_baseline_and_mutation_reward: {path}")
    return cells, warnings


def _labels(results: list[dict[str, Any]]) -> tuple[list[bool], list[bool], list[bool]]:
    positives = [decision_is_positive(r["gate_decision"]) for r in results]
    breakage = [bool(r["eval_agent_breakage_label"]) for r in results]
    silent = [bool(r["eval_silent_regression_label"]) for r in results]
    return positives, breakage, silent


def _safe_div(a: float, b: float) -> float | None:
    return a / b if b else None


def _method_metrics(
    method: str,
    results: list[dict[str, Any]],
    exhaustive_tests: int,
) -> dict[str, Any]:
    positives, breakage, silent = _labels(results)
    tp = sum(1 for p, y in zip(positives, breakage) if p and y)
    fp = sum(1 for p, y in zip(positives, breakage) if p and not y)
    fn = sum(1 for p, y in zip(positives, breakage) if (not p) and y)
    tn = sum(1 for p, y in zip(positives, breakage) if (not p) and not y)
    silent_tp = sum(1 for p, y in zip(positives, silent) if p and y)
    silent_fn = sum(1 for p, y in zip(positives, silent) if (not p) and y)
    tests_run = sum(int(r.get("tests_run") or 0) for r in results)
    schema_compatible_blocks = sum(
        1
        for r in results
        if r["gate_decision"] == "block"
        and r.get("schema_checker_pass")
        and r.get("typed_client_checker_pass")
        and r.get("eval_agent_breakage_label")
    )
    warning_decisions = [r for r in results if decision_is_positive(r["gate_decision"])]
    warning_quality = _safe_div(
        sum(1 for r in warning_decisions if r.get("eval_agent_breakage_label") or r.get("semantic_oracle_pass") is False),
        len(warning_decisions),
    )
    return {
        "method": method,
        "cells": len(results),
        "silent_regression_recall": _safe_div(silent_tp, silent_tp + silent_fn),
        "agent_breakage_recall": _safe_div(tp, tp + fn),
        "precision": _safe_div(tp, tp + fp),
        "false_positive_rate": _safe_div(fp, fp + tn),
        "false_negative_rate": _safe_div(fn, fn + tp),
        "tests_run": tests_run,
        "relative_test_cost": _safe_div(tests_run, exhaustive_tests),
        "reduction_vs_exhaustive": None
        if exhaustive_tests == 0
        else 1.0 - (tests_run / exhaustive_tests),
        "lift_over_schema_checker": None,
        "blocked_schema_compatible_regressions": schema_compatible_blocks,
        "warning_quality": warning_quality,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "silent_tp": silent_tp,
        "silent_fn": silent_fn,
    }


def _fill_lift(metrics: list[dict[str, Any]]) -> None:
    base = next((m for m in metrics if m["method"] == "SchemaCheckerOnly"), None)
    base_recall = (base or {}).get("agent_breakage_recall") or 0.0
    for m in metrics:
        recall = m.get("agent_breakage_recall")
        m["lift_over_schema_checker"] = None if recall is None else recall - base_recall


def _fmt(x: Any) -> str:
    if x is None:
        return "NA"
    if isinstance(x, float):
        return f"{x:.3f}"
    return str(x)


def _write_md(path: Path, metrics: list[dict[str, Any]], warnings: list[str], inputs: list[Path]) -> None:
    lines = [
        "# AFC-Gate Evaluation Summary",
        "",
        "Inputs:",
    ]
    lines.extend(f"- `{p}`" for p in inputs)
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {w}" for w in warnings)
    lines.extend(
        [
            "",
            "| Method | Recall | Silent Recall | Precision | FPR | Tests Run | Cost vs Exhaustive | Notes |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for m in metrics:
        notes = (
            f"blocked_schema_compatible={m['blocked_schema_compatible_regressions']}; "
            f"lift={_fmt(m['lift_over_schema_checker'])}; warning_quality={_fmt(m['warning_quality'])}"
        )
        lines.append(
            f"| {m['method']} | {_fmt(m['agent_breakage_recall'])} | "
            f"{_fmt(m['silent_regression_recall'])} | {_fmt(m['precision'])} | "
            f"{_fmt(m['false_positive_rate'])} | {m['tests_run']} | "
            f"{_fmt(m['relative_test_cost'])} | {notes} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _latex_escape(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
    )


def _write_tex(path: Path, metrics: list[dict[str, Any]]) -> None:
    lines = [
        "% Auto-generated by code/schema_mutation/evaluate_gate.py",
        "\\begin{tabular}{lrrrrr}",
        "\\hline",
        "Method & Recall & Precision & FPR & Tests & Cost \\\\",
        "\\hline",
    ]
    for m in metrics:
        lines.append(
            f"{_latex_escape(m['method'])} & {_fmt(m['agent_breakage_recall'])} & "
            f"{_fmt(m['precision'])} & {_fmt(m['false_positive_rate'])} & "
            f"{m['tests_run']} & {_fmt(m['relative_test_cost'])} \\\\"
        )
    lines.extend(["\\hline", "\\end{tabular}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_plot(path: Path, metrics: list[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable; skipping plot: {exc}")
        return
    if not metrics:
        print("[warn] no metrics; skipping plot")
        return
    markers = ["o", "s", "^", "D", "x", "+", "*"]
    fig, ax = plt.subplots(figsize=(5.4, 3.3))
    for i, m in enumerate(metrics):
        x = m.get("relative_test_cost")
        y = m.get("silent_regression_recall")
        if x is None or y is None:
            continue
        ax.scatter(x, y, marker=markers[i % len(markers)], color="0.2", s=42)
        ax.annotate(m["method"], (x, y), xytext=(4, 4), textcoords="offset points", fontsize=7)
    ax.set_xlabel("Relative test cost")
    ax.set_ylabel("Silent regression recall")
    ax.set_xlim(-0.03, 1.03)
    ax.set_ylim(-0.03, 1.03)
    ax.grid(True, color="0.85", linewidth=0.6)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _discover_inputs(args: argparse.Namespace) -> list[Path]:
    if args.inputs:
        return [Path(x) if Path(x).is_absolute() else _REPO_ROOT / x for x in args.inputs]
    paths = list(DEFAULT_PAIRED_ARTIFACTS)
    if args.input_existing_artifacts:
        if getattr(args, "include_phase5_observability", False):
            for pattern in PHASE5_OBSERVABILITY_PATTERNS:
                paths.extend(sorted(RUNS.glob(pattern)))
        return _dedup_paths(paths)
    return _dedup_paths(paths)


def _dedup_paths(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("inputs", nargs="*", help="paired JSONL inputs")
    p.add_argument("--input-existing-artifacts", action="store_true")
    p.add_argument("--include-phase5-observability", action="store_true")
    p.add_argument("--overwrite", action="store_true", help="accepted for workflow symmetry; output files are overwritten")
    p.add_argument("--budget", default="10", help="replay budget: integer or all")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--include-fake", action="store_true")
    args = p.parse_args()

    inputs = _discover_inputs(args)
    budget = parse_budget(args.budget)
    cells, warnings = _load_cells(inputs, include_fake=args.include_fake)

    split_dir = RUNS / "split_day6"
    if split_dir.exists():
        warnings.append("split_day6 artifacts detected but skipped: they are not paired baseline/mutation rows")

    if args.dry_run:
        print("[gate] dry-run")
        print(f"inputs={len(inputs)}")
        for pth in inputs:
            print(f"  {pth}")
        print(f"paired_cells={len(cells)}")
        print(f"budget={args.budget}")
        print(f"methods={','.join(GATE_METHODS)}")
        for w in warnings:
            print(f"[warn] {w}")
        return 0

    all_results: list[dict[str, Any]] = []
    by_method: dict[str, list[dict[str, Any]]] = {}
    for method in GATE_METHODS:
        method_budget = None if method == "ExhaustiveReplayOracle" else budget
        config = GateConfig(method=method, replay_budget=method_budget, seed=args.seed)
        results = run_gate(cells, config)
        by_method[method] = results
        all_results.extend(results)

    exhaustive_tests = max(1, sum(r.get("tests_run", 0) for r in by_method["ExhaustiveReplayOracle"]))
    metrics = [_method_metrics(method, by_method[method], exhaustive_tests) for method in GATE_METHODS]
    _fill_lift(metrics)

    RUNS.mkdir(parents=True, exist_ok=True)
    table_dir = PAPER / "tables"
    fig_dir = PAPER / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    out_json = RUNS / "gate_evaluation_summary.json"
    out_md = RUNS / "gate_evaluation_summary.md"
    out_records = RUNS / "gate_evaluation_records.jsonl"
    out_tex = table_dir / "gate_evaluation_auto.tex"
    out_pdf = fig_dir / "gate_recall_cost_tradeoff.pdf"

    with out_records.open("w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    out_json.write_text(
        json.dumps(
            {
                "inputs": [str(p) for p in inputs],
                "warnings": warnings,
                "cells": len(cells),
                "budget": args.budget,
                "metrics": metrics,
                "gate_records_path": str(out_records),
                "gate_results_sample": all_results[:50],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_md(out_md, metrics, warnings, inputs)
    _write_tex(out_tex, metrics)
    _write_plot(out_pdf, metrics)

    print(f"cells={len(cells)}")
    for w in warnings:
        print(f"[warn] {w}")
    print(f"summary_json={out_json}")
    print(f"summary_md={out_md}")
    print(f"records_jsonl={out_records}")
    print(f"summary_tex={out_tex}")
    if out_pdf.exists():
        print(f"summary_pdf={out_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
