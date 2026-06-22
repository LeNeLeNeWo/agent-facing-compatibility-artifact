"""Offline Phase 10D analysis for non-obviousness formal results.

This script performs no model/API calls. It reads Phase 10C formal status rows
and the Phase 10 non-obviousness plan, then writes analysis reports and
paper-ready assets.
"""

from __future__ import annotations

import json
import math
import random
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import chi2_contingency, fisher_exact


ROOT = Path(__file__).resolve().parents[2]
PHASE10 = ROOT / "runs" / "schema_mutation" / "phase10"
FORMAL = PHASE10 / "phase10c" / "nonobviousness_formal"
PLAN = PHASE10 / "nonobviousness" / "nonobviousness_control_plan.jsonl"
OUT = PHASE10 / "phase10d_nonobviousness_analysis"
TABLE_OUT = ROOT / "IEEE_Conference_Template" / "tables" / "nonobviousness_control_auto.tex"
FIG_OUT = ROOT / "IEEE_Conference_Template" / "figures" / "nonobviousness_control.pdf"
PHASE5_STATUS = ROOT / "runs" / "schema_mutation" / "phase5" / "status"

CONDITION_ORDER = [
    "O0_increased_reasoning_budget",
    "O0_reflection_scaffold",
    "rule_in_tool_preamble_upper_bound",
]
CONDITION_LABELS = {
    "O0_increased_reasoning_budget": "O0 + more reasoning",
    "O0_reflection_scaffold": "O0 + reflection",
    "rule_in_tool_preamble_upper_bound": "Rule-visible upper bound",
}
REFERENCE_LABELS = {
    "O0_standard_reference": "O0 standard reference",
    "O1_generic_error_reference": "O1 generic error reference",
}
BOOTSTRAP_N = 20000
BOOTSTRAP_SEED = 10019


def stable_seed(*parts: Any) -> int:
    text = "::".join(str(p) for p in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return BOOTSTRAP_SEED + int(digest[:8], 16)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{100 * value:.1f}%"


def rate(success: int, n: int) -> float | None:
    return None if n == 0 else success / n


def ci(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"lo": None, "hi": None}
    arr = np.array(values, dtype=float)
    return {"lo": float(np.quantile(arr, 0.025)), "hi": float(np.quantile(arr, 0.975))}


def status_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((FORMAL / "status").glob("nonobviousness_[0-9][0-9][0-9][0-9]_status.jsonl")):
        for row in read_jsonl(path):
            row = dict(row)
            row["_status_file"] = path.name
            rows.append(row)
    return rows


def plan_rows() -> list[dict[str, Any]]:
    return read_jsonl(PLAN)


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for cond in CONDITION_ORDER:
        cond_rows = [r for r in rows if r.get("condition") == cond]
        ok = [r for r in cond_rows if r.get("status") == "ok"]
        success = sum(1 for r in ok if r.get("mutation_success") is True or float(r.get("reward") or 0) > 0)
        hidden = sum(1 for r in ok if r.get("hidden_business_rule_violation") is True)
        steps = [float(r.get("num_actions") or 0) for r in ok if r.get("num_actions") is not None]
        out[cond] = {
            "label": CONDITION_LABELS[cond],
            "planned_n": len(cond_rows),
            "observed_n": len(cond_rows),
            "ok_n": len(ok),
            "status_counts": dict(Counter(str(r.get("status")) for r in cond_rows)),
            "success_n": success,
            "success_rate": rate(success, len(ok)),
            "hidden_violation_n": hidden,
            "hidden_violation_rate": rate(hidden, len(ok)),
            "provider_error_n": sum(1 for r in cond_rows if r.get("status") == "provider_error"),
            "timeout_n": sum(1 for r in cond_rows if r.get("status") == "timeout"),
            "failed_n": sum(1 for r in cond_rows if r.get("status") == "failed"),
            "avg_steps": None if not steps else sum(steps) / len(steps),
            "avg_token_cost": None,
        }
    return out


def split_summary(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, dict[str, Any]]]:
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for cond in CONDITION_ORDER:
        cond_rows = [r for r in rows if r.get("condition") == cond]
        field_values = sorted({str(r.get(field)) for r in cond_rows})
        result[cond] = {}
        for value in field_values:
            subset = [r for r in cond_rows if str(r.get(field)) == value]
            ok = [r for r in subset if r.get("status") == "ok"]
            success = sum(1 for r in ok if r.get("mutation_success") is True or float(r.get("reward") or 0) > 0)
            hidden = sum(1 for r in ok if r.get("hidden_business_rule_violation") is True)
            result[cond][value] = {
                "observed_n": len(subset),
                "ok_n": len(ok),
                "status_counts": dict(Counter(str(r.get("status")) for r in subset)),
                "success_n": success,
                "success_rate": rate(success, len(ok)),
                "hidden_violation_n": hidden,
                "hidden_violation_rate": rate(hidden, len(ok)),
            }
    return result


def bootstrap_rates(rows: list[dict[str, Any]], condition: str, n_boot: int = BOOTSTRAP_N) -> dict[str, Any]:
    ok = [r for r in rows if r.get("condition") == condition and r.get("status") == "ok"]
    values = [1.0 if (r.get("mutation_success") is True or float(r.get("reward") or 0) > 0) else 0.0 for r in ok]
    rng = random.Random(stable_seed("rate", condition))
    reps: list[float] = []
    if values:
        for _ in range(n_boot):
            sample = [values[rng.randrange(len(values))] for _ in values]
            reps.append(sum(sample) / len(sample))
    point = sum(values) / len(values) if values else None
    return {"point": point, "ci95": ci(reps), "n_boot": n_boot}


def bootstrap_diff(
    rows: list[dict[str, Any]],
    a: str,
    b: str,
    n_boot: int = BOOTSTRAP_N,
) -> dict[str, Any]:
    vals_a = [
        1.0 if (r.get("mutation_success") is True or float(r.get("reward") or 0) > 0) else 0.0
        for r in rows
        if r.get("condition") == a and r.get("status") == "ok"
    ]
    vals_b = [
        1.0 if (r.get("mutation_success") is True or float(r.get("reward") or 0) > 0) else 0.0
        for r in rows
        if r.get("condition") == b and r.get("status") == "ok"
    ]
    rng = random.Random(stable_seed("diff", a, b))
    reps: list[float] = []
    if vals_a and vals_b:
        for _ in range(n_boot):
            ra = sum(vals_a[rng.randrange(len(vals_a))] for _ in vals_a) / len(vals_a)
            rb = sum(vals_b[rng.randrange(len(vals_b))] for _ in vals_b) / len(vals_b)
            reps.append(ra - rb)
    point = (sum(vals_a) / len(vals_a) - sum(vals_b) / len(vals_b)) if vals_a and vals_b else None
    return {"a": a, "b": b, "point": point, "ci95": ci(reps), "n_boot": n_boot}


def cluster_bootstrap_diff(
    rows: list[dict[str, Any]],
    a: str,
    b: str,
    n_boot: int = BOOTSTRAP_N,
) -> dict[str, Any]:
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get("source_o0_cell_key") or row.get("source_baseline_cell_key") or row.get("task_id"))
        clusters[key].append(row)
    keys = sorted(clusters)
    rng = random.Random(stable_seed("cluster", a, b))

    def cond_rate(sample_rows: list[dict[str, Any]], cond: str) -> float | None:
        ok = [r for r in sample_rows if r.get("condition") == cond and r.get("status") == "ok"]
        if not ok:
            return None
        s = sum(1 for r in ok if r.get("mutation_success") is True or float(r.get("reward") or 0) > 0)
        return s / len(ok)

    reps: list[float] = []
    for _ in range(n_boot):
        sample_rows: list[dict[str, Any]] = []
        for _ in keys:
            sample_rows.extend(clusters[rng.choice(keys)])
        ra = cond_rate(sample_rows, a)
        rb = cond_rate(sample_rows, b)
        if ra is not None and rb is not None:
            reps.append(ra - rb)
    point_a = cond_rate(rows, a)
    point_b = cond_rate(rows, b)
    return {
        "a": a,
        "b": b,
        "point": None if point_a is None or point_b is None else point_a - point_b,
        "ci95": ci(reps),
        "n_boot": n_boot,
        "clusters": len(keys),
    }


def fisher_and_chi2(rows: list[dict[str, Any]], a: str, b: str) -> dict[str, Any]:
    def table_counts(cond: str) -> tuple[int, int]:
        ok = [r for r in rows if r.get("condition") == cond and r.get("status") == "ok"]
        success = sum(1 for r in ok if r.get("mutation_success") is True or float(r.get("reward") or 0) > 0)
        return success, len(ok) - success

    a_success, a_fail = table_counts(a)
    b_success, b_fail = table_counts(b)
    table = [[a_success, a_fail], [b_success, b_fail]]
    odds, fisher_p = fisher_exact(table, alternative="two-sided")
    chi2, chi_p, dof, expected = chi2_contingency(table, correction=False)
    return {
        "a": a,
        "b": b,
        "table": table,
        "fisher_oddsratio": None if math.isinf(float(odds)) else float(odds),
        "fisher_p": float(fisher_p),
        "chi2": float(chi2),
        "chi2_p": float(chi_p),
        "chi2_dof": int(dof),
        "chi2_expected": [[float(x) for x in row] for row in expected],
    }


def sensitivity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    as_planned: dict[str, Any] = {}
    ok_only: dict[str, Any] = {}
    for cond in CONDITION_ORDER:
        cond_rows = [r for r in rows if r.get("condition") == cond]
        ok = [r for r in cond_rows if r.get("status") == "ok"]
        success = sum(1 for r in ok if r.get("mutation_success") is True or float(r.get("reward") or 0) > 0)
        hidden = sum(1 for r in ok if r.get("hidden_business_rule_violation") is True)
        as_planned[cond] = {
            "success_rate_counting_non_ok_as_missing_not_failure": rate(success, len(cond_rows)),
            "hidden_violation_rate_counting_non_ok_as_missing_not_failure": rate(hidden, len(cond_rows)),
            "denominator": len(cond_rows),
        }
        ok_only[cond] = {
            "success_rate": rate(success, len(ok)),
            "hidden_violation_rate": rate(hidden, len(ok)),
            "denominator": len(ok),
        }
    return {"as_planned_denominator": as_planned, "ok_only_primary": ok_only}


def find_prior_reference(plan: list[dict[str, Any]]) -> dict[str, Any]:
    source_o0_keys = {str(r.get("source_o0_cell_key")) for r in plan if r.get("source_o0_cell_key")}
    # Load only relevant status files for speed and to avoid smoke/GPT/WYZ rows.
    candidate_files = [
        p
        for p in sorted(PHASE5_STATUS.glob("*status.jsonl"))
        if "smoke" not in p.name and "retry" not in p.name and "wyz" not in p.name.lower() and "gpt" not in p.name.lower()
    ]
    by_key: dict[str, dict[str, Any]] = {}
    o1_candidates: list[dict[str, Any]] = []
    for path in candidate_files:
        for row in read_jsonl(path):
            key = str(row.get("cell_key"))
            if key in source_o0_keys:
                by_key[key] = row
            if row.get("observability_level") == "O1_generic_error" or row.get("condition") == "O1_generic_error":
                o1_candidates.append(row)
    matched_o0 = [by_key[k] for k in sorted(source_o0_keys) if k in by_key]
    o0_ok = [r for r in matched_o0 if r.get("status") == "ok"]
    o0_success = sum(1 for r in o0_ok if r.get("mutation_success") is True or float(r.get("reward") or 0) > 0)
    o0_hidden = sum(1 for r in o0_ok if r.get("hidden_business_rule_violation") is True)
    # O1 is not guaranteed to be generated for the same C1-C4 Phase 10 plan. Only
    # count exact source-baseline/model/env/task/seed matches when present.
    plan_keys = {
        (
            str(r.get("source_baseline_cell_key")),
            str(r.get("env")),
            str(r.get("model")),
            str(r.get("task_id")),
            str(r.get("seed")),
            str(r.get("mutation_name")),
        )
        for r in plan
    }
    matched_o1: list[dict[str, Any]] = []
    for row in o1_candidates:
        key = (
            str(row.get("source_baseline_cell_key")),
            str(row.get("env")),
            str(row.get("model")),
            str(row.get("task_id")),
            str(row.get("seed")),
            str(row.get("mutation_name")),
        )
        if key in plan_keys:
            matched_o1.append(row)
    o1_ok = [r for r in matched_o1 if r.get("status") == "ok"]
    o1_success = sum(1 for r in o1_ok if r.get("mutation_success") is True or float(r.get("reward") or 0) > 0)
    o1_hidden = sum(1 for r in o1_ok if r.get("hidden_business_rule_violation") is True)
    return {
        "O0_standard_reference": {
            "source": "matched prior rows via source_o0_cell_key",
            "matched_n": len(matched_o0),
            "ok_n": len(o0_ok),
            "success_n": o0_success,
            "success_rate": rate(o0_success, len(o0_ok)),
            "hidden_violation_n": o0_hidden,
            "hidden_violation_rate": rate(o0_hidden, len(o0_ok)),
        },
        "O1_generic_error_reference": {
            "source": "attempted exact match from prior frozen status rows",
            "matched_n": len(matched_o1),
            "ok_n": len(o1_ok),
            "success_n": o1_success,
            "success_rate": rate(o1_success, len(o1_ok)),
            "hidden_violation_n": o1_hidden,
            "hidden_violation_rate": rate(o1_hidden, len(o1_ok)),
            "usable_as_matched_reference": len(o1_ok) == len(source_o0_keys),
        },
    }


def integrity_audit(rows: list[dict[str, Any]], plan: list[dict[str, Any]]) -> dict[str, Any]:
    leakage: list[dict[str, Any]] = []
    upper_visible_missing = 0
    forbidden_models = []
    for row in plan:
        cond = str(row.get("condition"))
        drift = str(row.get("business_rule_drift") or "")
        variant = str(row.get("agent_prompt_variant") or "")
        level = str(row.get("observability_level") or "")
        model_text = f"{row.get('provider')}/{row.get('model')}".lower()
        if any(x in model_text for x in ("gpt", "wyz", "grok")):
            forbidden_models.append({"cell_key": row.get("cell_key"), "model": row.get("model"), "provider": row.get("provider")})
        if cond in {"O0_increased_reasoning_budget", "O0_reflection_scaffold"}:
            if level != "O0_silent" or variant == "rule_visible_preamble" or "evolved API rule is" in drift or "migration note" in drift.lower() or "rule-visible" in drift.lower():
                leakage.append({"cell_key": row.get("cell_key"), "condition": cond})
        if cond == "rule_in_tool_preamble_upper_bound":
            if level != "O4_migration_note" or variant != "rule_visible_preamble":
                upper_visible_missing += 1
    status_counts = Counter(str(r.get("status")) for r in rows)
    return {
        "planned_cells": len(plan),
        "status_rows": len(rows),
        "status_counts": dict(status_counts),
        "o0_rule_leakage_issues": leakage,
        "rule_visible_upper_bound_missing_visibility_count": upper_visible_missing,
        "fake_rows": sum(1 for r in rows if r.get("fake_run") is True),
        "baseline_success_false_rows": sum(1 for r in rows if r.get("baseline_success") is not True),
        "schema_changed_not_false_rows": sum(1 for r in rows if r.get("schema_changed") is not False),
        "forbidden_model_rows": forbidden_models,
        "provider_error_rows": status_counts.get("provider_error", 0),
        "timeout_rows": status_counts.get("timeout", 0),
        "failed_rows": status_counts.get("failed", 0),
        "provider_error_timeout_failed_not_counted_as_agent_failures": True,
        "parse_cleanly": True,
        "artifact_isolation": {
            "phase10d_writes": [
                "runs/schema_mutation/phase10/phase10d_nonobviousness_analysis",
                "IEEE_Conference_Template/tables/nonobviousness_control_auto.tex",
                "IEEE_Conference_Template/figures/nonobviousness_control.pdf",
            ],
            "paper_body_modified": False,
            "phase5_or_phase8_rerun": False,
        },
    }


def write_table(summary: dict[str, dict[str, Any]], references: dict[str, Any]) -> None:
    TABLE_OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for cond in CONDITION_ORDER:
        item = summary[cond]
        rows.append(
            (
                item["label"],
                str(item["ok_n"]),
                f"{item['success_n']}/{item['ok_n']} ({pct(item['success_rate'])})",
                f"{item['hidden_violation_n']}/{item['ok_n']} ({pct(item['hidden_violation_rate'])})",
                "no visible rule" if cond != "rule_in_tool_preamble_upper_bound" else "rule visible",
            )
        )
    o0 = references.get("O0_standard_reference", {})
    if o0.get("ok_n"):
        rows.append(
            (
                "O0 standard reference",
                str(o0["ok_n"]),
                f"{o0['success_n']}/{o0['ok_n']} ({pct(o0['success_rate'])})",
                f"{o0['hidden_violation_n']}/{o0['ok_n']} ({pct(o0['hidden_violation_rate'])})",
                "matched prior",
            )
        )
    lines = [
        "% Auto-generated by code/schema_mutation/phase10_analyze_nonobviousness.py",
        "\\begin{table}[t]",
        "\\centering",
        "\\caption{Non-obviousness control: extra reasoning without visibility does not provide the recovery channel, while making the evolved rule visible gives an upper-bound recovery signal.}",
        "\\label{tab:nonobviousness-control}",
            "\\small",
            "\\begin{tabular}{p{0.28\\linewidth}rccp{0.20\\linewidth}}",
        "\\toprule",
        "Condition & N & Success & Hidden violation & Interpretation \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(row) + " \\\\")
    lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\vspace{0.3em}",
            "\\footnotesize{N counts ok rows only; one reflection cell failed and one rule-visible cell timed out, and these infrastructure rows are not counted as agent failures. The O0 standard reference row, when shown, is a matched prior frozen-result reference rather than a new Phase 10C call.}",
            "\\end{table}",
            "",
        ]
    )
    TABLE_OUT.write_text("\n".join(lines), encoding="utf-8")


def write_figure(summary: dict[str, dict[str, Any]]) -> None:
    FIG_OUT.parent.mkdir(parents=True, exist_ok=True)
    labels = [summary[c]["label"] for c in CONDITION_ORDER]
    success = [summary[c]["success_rate"] or 0.0 for c in CONDITION_ORDER]
    hidden = [summary[c]["hidden_violation_rate"] or 0.0 for c in CONDITION_ORDER]
    y = np.arange(len(labels))
    plt.rcParams.update({"font.size": 8})
    fig, ax = plt.subplots(figsize=(5.2, 2.2))
    ax.barh(y + 0.16, success, height=0.28, label="Success", color="#2f6f9f")
    ax.barh(y - 0.16, hidden, height=0.28, label="Hidden violation", color="#b45f4d")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Rate among ok rows")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(loc="lower right", frameon=False)
    fig.tight_layout()
    fig.savefig(FIG_OUT)
    plt.close(fig)


def write_text_snippet(summary: dict[str, dict[str, Any]], stats: dict[str, Any]) -> None:
    path = OUT / "paper_text_snippet.md"
    short = (
        "Short version\n\n"
        "We add a non-obviousness control to separate reasoning effort from semantic visibility. "
        "For the same class of silent semantic drifts, increasing the action/reasoning budget produced "
        f"{summary['O0_increased_reasoning_budget']['success_n']}/{summary['O0_increased_reasoning_budget']['ok_n']} "
        f"successes ({pct(summary['O0_increased_reasoning_budget']['success_rate'])}), and adding a generic "
        f"reflection scaffold produced {summary['O0_reflection_scaffold']['success_n']}/{summary['O0_reflection_scaffold']['ok_n']} "
        f"successes ({pct(summary['O0_reflection_scaffold']['success_rate'])}). Both conditions retained high hidden-rule "
        f"violation rates ({pct(summary['O0_increased_reasoning_budget']['hidden_violation_rate'])} and "
        f"{pct(summary['O0_reflection_scaffold']['hidden_violation_rate'])}). In contrast, when the evolved rule was "
        f"made visible as an upper-bound prompt/tool-preamble signal, success rose to "
        f"{summary['rule_in_tool_preamble_upper_bound']['success_n']}/{summary['rule_in_tool_preamble_upper_bound']['ok_n']} "
        f"({pct(summary['rule_in_tool_preamble_upper_bound']['success_rate'])}) with no hidden violations among ok rows. "
        "This does not show that prompting is useless; rather, reasoning helps use visible signals, but cannot reliably "
        "recover an external rule change that remains unobserved."
    )
    medium = (
        "Medium version\n\n"
        "To address the possibility that the O0 failures are merely a weak-reasoning artifact, we ran a matched "
        "non-obviousness control over the Phase 10C formal cells. The control keeps the semantic drift silent while "
        "varying only the agent-side recovery channel. With a larger reasoning/action budget, agents succeeded in "
        f"{summary['O0_increased_reasoning_budget']['success_n']}/{summary['O0_increased_reasoning_budget']['ok_n']} "
        f"ok cells ({pct(summary['O0_increased_reasoning_budget']['success_rate'])}), while hidden-rule violations remained "
        f"at {pct(summary['O0_increased_reasoning_budget']['hidden_violation_rate'])}. A generic plan-and-check/reflection "
        f"scaffold improved the point estimate only slightly, to "
        f"{summary['O0_reflection_scaffold']['success_n']}/{summary['O0_reflection_scaffold']['ok_n']} "
        f"({pct(summary['O0_reflection_scaffold']['success_rate'])}), with hidden violations still at "
        f"{pct(summary['O0_reflection_scaffold']['hidden_violation_rate'])}. By contrast, the rule-visible upper-bound "
        f"condition succeeded in {summary['rule_in_tool_preamble_upper_bound']['success_n']}/{summary['rule_in_tool_preamble_upper_bound']['ok_n']} "
        f"ok cells ({pct(summary['rule_in_tool_preamble_upper_bound']['success_rate'])}) and had no hidden-rule violations "
        "among ok rows. Bootstrap contrasts show a large upper-bound advantage over both silent conditions. "
        "We therefore interpret the limiting factor as semantic observability rather than reasoning effort alone: "
        "additional reasoning can help an agent act on available evidence, but it does not create access to an external "
        "business-rule change that the schema, prompt, and runtime feedback do not expose. These results are a "
        "supplemental control; primary rates use ok rows only, with the one failed reflection cell and one "
        "rule-visible timeout treated as infrastructure non-ok rows rather than agent failures."
    )
    path.write_text(short + "\n\n---\n\n" + medium + "\n", encoding="utf-8")


def write_audit(audit: dict[str, Any]) -> None:
    write_json(OUT / "integrity_audit.json", audit)
    lines = [
        "# Phase 10D Integrity Audit",
        "",
        f"- Planned cells: {audit['planned_cells']}",
        f"- Status rows: {audit['status_rows']}",
        "- Status counts: " + ", ".join(f"{k}={v}" for k, v in sorted(audit["status_counts"].items())),
        f"- O0 rule leakage issues: {len(audit['o0_rule_leakage_issues'])}",
        f"- Rule-visible upper-bound missing-visibility count: {audit['rule_visible_upper_bound_missing_visibility_count']}",
        f"- Fake rows: {audit['fake_rows']}",
        f"- Baseline-success false rows: {audit['baseline_success_false_rows']}",
        f"- Schema-changed-not-false rows: {audit['schema_changed_not_false_rows']}",
        f"- Forbidden GPT/WYZ/Grok planned rows: {len(audit['forbidden_model_rows'])}",
        f"- Provider errors: {audit['provider_error_rows']}",
        f"- Timeouts: {audit['timeout_rows']}",
        f"- Failed rows: {audit['failed_rows']}",
        "- Provider_error/timeout/failed counted as agent failures: no",
        "- Raw Phase 5/8 artifacts modified by Phase 10D: no; this phase is offline analysis only.",
        "",
    ]
    (OUT / "integrity_audit.md").write_text("\n".join(lines), encoding="utf-8")


def write_report(analysis: dict[str, Any]) -> None:
    s = analysis["condition_summary"]
    stats = analysis["statistics"]
    lines = [
        "# Phase 10D Non-Obviousness Analysis Report",
        "",
        "## 1. Executive Summary",
        "",
        f"- Formal cells analyzed: {analysis['integrity']['status_rows']} terminal status rows.",
        "- Status counts: " + ", ".join(f"{k}={v}" for k, v in sorted(analysis["integrity"]["status_counts"].items())),
        "- Headline result: silent extra reasoning and silent reflection remain low-recovery, while the rule-visible upper bound recovers substantially more often.",
        f"- Supports non-obviousness critique response: {analysis['supports_mechanism_interpretation']}.",
        "",
        "## 2. Condition-Level Results",
        "",
        "| condition | N ok | success | hidden violation | non-ok | avg steps |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cond in CONDITION_ORDER:
        row = s[cond]
        non_ok = row["provider_error_n"] + row["timeout_n"] + row["failed_n"]
        avg_steps = "n/a" if row["avg_steps"] is None else f"{row['avg_steps']:.1f}"
        lines.append(
            f"| {row['label']} | {row['ok_n']} | {row['success_n']}/{row['ok_n']} ({pct(row['success_rate'])}) | "
            f"{row['hidden_violation_n']}/{row['ok_n']} ({pct(row['hidden_violation_rate'])}) | {non_ok} | {avg_steps} |"
        )
    lines.extend(
        [
            "",
            "Reference rows:",
            "",
        ]
    )
    for key, ref in analysis["references"].items():
        usable = ref.get("usable_as_matched_reference", True)
        lines.append(
            f"- {REFERENCE_LABELS.get(key, key)}: matched={ref.get('matched_n')}, ok={ref.get('ok_n')}, "
            f"success={ref.get('success_n')}/{ref.get('ok_n')} ({pct(ref.get('success_rate'))}), "
            f"hidden={ref.get('hidden_violation_n')}/{ref.get('ok_n')} ({pct(ref.get('hidden_violation_rate'))}), "
            f"fully matched={usable}."
        )
    lines.extend(["", "## 3. Statistical Analysis", ""])
    lines.append("Bootstrap success-rate CIs:")
    for cond, item in stats["bootstrap_success_rates"].items():
        lines.append(f"- {CONDITION_LABELS[cond]}: {pct(item['point'])} CI [{pct(item['ci95']['lo'])}, {pct(item['ci95']['hi'])}]")
    lines.append("")
    lines.append("Bootstrap differences:")
    for key, item in stats["bootstrap_differences"].items():
        lines.append(f"- {key}: {pct(item['point'])} CI [{pct(item['ci95']['lo'])}, {pct(item['ci95']['hi'])}]")
    lines.append("")
    lines.append("Cluster bootstrap by source reference cell:")
    for key, item in stats["cluster_bootstrap_differences"].items():
        lines.append(
            f"- {key}: {pct(item['point'])} CI [{pct(item['ci95']['lo'])}, {pct(item['ci95']['hi'])}], clusters={item['clusters']}"
        )
    lines.append("")
    lines.append("Fisher exact / chi-square tests:")
    for key, item in stats["tests"].items():
        lines.append(
            f"- {key}: Fisher p={item['fisher_p']:.3g}, chi-square p={item['chi2_p']:.3g}, table={item['table']}"
        )
    lines.extend(
        [
            "",
            "Sensitivity analysis: provider_error/timeout/failed rows are not counted as agent failures. Primary rates use ok rows only; as-planned denominator rates are provided in the JSON report.",
            "",
            "## 4. By Domain / Model / C-Class",
            "",
            "Breakdowns are in `nonobviousness_analysis_report.json` under `by_domain`, `by_model`, and `by_semantic_class`. Some cells are small after splitting, so these are diagnostic rather than primary inferential results.",
            "",
            "## 5. Integrity Audit",
            "",
            f"- Rule leakage detected: {bool(analysis['integrity']['o0_rule_leakage_issues'])}.",
            f"- Provider errors: {analysis['integrity']['provider_error_rows']}.",
            f"- Fake rows: {analysis['integrity']['fake_rows']}.",
            f"- Baseline-success false rows: {analysis['integrity']['baseline_success_false_rows']}.",
            "- Artifact isolation: Phase 10D did not run agents and did not modify Phase 5/8 raw artifacts or paper body files.",
            "",
            "## 6. Paper-Ready Assets",
            "",
            f"- Table: `{TABLE_OUT.relative_to(ROOT)}`",
            f"- Figure: `{FIG_OUT.relative_to(ROOT)}`",
            f"- Text snippet: `{(OUT / 'paper_text_snippet.md').relative_to(ROOT)}`",
            "",
            "## 7. Recommendation",
            "",
            "Integrate into the paper as a small supplemental control, with an explicit note that the one failed reflection cell and one rule-visible timeout are excluded from ok-row rates and are not counted as agent failures. No retry is required for the central contrast, though retrying the two infrastructure rows would make denominators tidier. The result is strong enough to address the obviousness critique, but it should be presented as a control rather than as a new main finding.",
            "",
            "## 8. What Not To Claim",
            "",
            "- Do not claim production frequency.",
            "- Do not claim human-validated oracle precision.",
            "- Do not claim all prompting fails.",
            "- Do not claim external validity beyond tested models/tasks.",
            "- Do not claim this replaces semantic observability.",
            "",
        ]
    )
    (OUT / "nonobviousness_analysis_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = status_rows()
    plan = plan_rows()
    summary = condition_summary(rows)
    comparisons = {
        "rule_visible_minus_o0_reasoning": ("rule_in_tool_preamble_upper_bound", "O0_increased_reasoning_budget"),
        "rule_visible_minus_o0_reflection": ("rule_in_tool_preamble_upper_bound", "O0_reflection_scaffold"),
        "o0_reflection_minus_o0_reasoning": ("O0_reflection_scaffold", "O0_increased_reasoning_budget"),
    }
    stats = {
        "bootstrap_success_rates": {cond: bootstrap_rates(rows, cond) for cond in CONDITION_ORDER},
        "bootstrap_differences": {name: bootstrap_diff(rows, a, b) for name, (a, b) in comparisons.items()},
        "cluster_bootstrap_differences": {
            name: cluster_bootstrap_diff(rows, a, b) for name, (a, b) in comparisons.items()
        },
        "tests": {name: fisher_and_chi2(rows, a, b) for name, (a, b) in comparisons.items()},
        "sensitivity": sensitivity(rows),
    }
    references = find_prior_reference(plan)
    audit = integrity_audit(rows, plan)
    analysis = {
        "condition_summary": summary,
        "by_domain": split_summary(rows, "env"),
        "by_model": split_summary(rows, "model"),
        "by_semantic_class": split_summary(rows, "semantic_class"),
        "statistics": stats,
        "references": references,
        "integrity": audit,
        "supports_mechanism_interpretation": bool(
            stats["bootstrap_differences"]["rule_visible_minus_o0_reasoning"]["ci95"]["lo"] is not None
            and stats["bootstrap_differences"]["rule_visible_minus_o0_reasoning"]["ci95"]["lo"] > 0
            and stats["bootstrap_differences"]["rule_visible_minus_o0_reflection"]["ci95"]["lo"] > 0
        ),
        "paths": {
            "analysis_dir": str(OUT.relative_to(ROOT)),
            "table": str(TABLE_OUT.relative_to(ROOT)),
            "figure": str(FIG_OUT.relative_to(ROOT)),
            "snippet": str((OUT / "paper_text_snippet.md").relative_to(ROOT)),
            "audit_md": str((OUT / "integrity_audit.md").relative_to(ROOT)),
            "audit_json": str((OUT / "integrity_audit.json").relative_to(ROOT)),
        },
    }
    write_json(OUT / "nonobviousness_analysis_report.json", analysis)
    write_audit(audit)
    write_table(summary, references)
    write_figure(summary)
    write_text_snippet(summary, stats)
    write_report(analysis)
    print(json.dumps({
        "analysis_dir": str(OUT),
        "status_rows": len(rows),
        "table": str(TABLE_OUT),
        "figure": str(FIG_OUT),
        "supports_mechanism_interpretation": analysis["supports_mechanism_interpretation"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
