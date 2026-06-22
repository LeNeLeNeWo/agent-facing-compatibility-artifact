"""Summarize Phase 10E real-changelog-grounded replay smoke results."""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PHASE10 = ROOT / "runs" / "schema_mutation" / "phase10"
REPLAY = PHASE10 / "real_case_replay"
SMOKE = REPLAY / "smoke"
DEFAULT_INPUT = SMOKE
DEFAULT_PLAN = SMOKE / "real_case_smoke_plan.jsonl"
DEFAULT_OUTPUT_MD = SMOKE / "real_case_smoke_summary.md"
DEFAULT_OUTPUT_JSON = SMOKE / "real_case_smoke_summary.json"
DEFAULT_REPORT = REPLAY / "phase10e_real_case_smoke_report.md"
AUDIT_JSON = REPLAY / "real_case_audit.json"

CONDITIONS = ["baseline_old_api", "evolved_o0_silent", "evolved_visible_feedback"]
COMPARISONS = {
    "baseline_old_api_vs_evolved_o0_silent": ("baseline_old_api", "evolved_o0_silent"),
    "evolved_o0_silent_vs_evolved_visible_feedback": ("evolved_o0_silent", "evolved_visible_feedback"),
    "baseline_old_api_vs_evolved_visible_feedback": ("baseline_old_api", "evolved_visible_feedback"),
}
BOOTSTRAP_N = 10000
BOOTSTRAP_SEED = 202610


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


def fmt_p(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4g}"


def rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def ci(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"lo": None, "hi": None}
    values = sorted(values)
    lo_idx = int(0.025 * (len(values) - 1))
    hi_idx = int(0.975 * (len(values) - 1))
    return {"lo": values[lo_idx], "hi": values[hi_idx]}


def success_value(row: dict[str, Any]) -> float:
    return 1.0 if row.get("mutation_success") is True else 0.0


def hidden_value(row: dict[str, Any]) -> float:
    return 1.0 if row.get("hidden_business_rule_violation") is True else 0.0


def mean(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)


def bootstrap_mean(values: list[float], seed: int, n_boot: int = BOOTSTRAP_N) -> dict[str, Any]:
    rng = random.Random(seed)
    reps: list[float] = []
    if values:
        for _ in range(n_boot):
            reps.append(sum(values[rng.randrange(len(values))] for _ in values) / len(values))
    return {"point": mean(values), "ci95": ci(reps), "n_boot": n_boot, "n": len(values)}


def bootstrap_diff(a_values: list[float], b_values: list[float], seed: int, n_boot: int = BOOTSTRAP_N) -> dict[str, Any]:
    rng = random.Random(seed)
    reps: list[float] = []
    if a_values and b_values:
        for _ in range(n_boot):
            a = sum(a_values[rng.randrange(len(a_values))] for _ in a_values) / len(a_values)
            b = sum(b_values[rng.randrange(len(b_values))] for _ in b_values) / len(b_values)
            reps.append(a - b)
    point = None if not a_values or not b_values else (sum(a_values) / len(a_values)) - (sum(b_values) / len(b_values))
    return {"point": point, "ci95": ci(reps), "n_boot": n_boot, "n_a": len(a_values), "n_b": len(b_values)}


def fisher_two_sided(table: list[list[int]]) -> float | None:
    a, b = table[0]
    c, d = table[1]
    n = a + b + c + d
    row1 = a + b
    col1 = a + c
    if n == 0:
        return None

    def hypergeom(x: int) -> float:
        return math.comb(col1, x) * math.comb(n - col1, row1 - x) / math.comb(n, row1)

    lo = max(0, row1 - (n - col1))
    hi = min(row1, col1)
    observed = hypergeom(a)
    p = 0.0
    for x in range(lo, hi + 1):
        px = hypergeom(x)
        if px <= observed + 1e-15:
            p += px
    return min(1.0, p)


def chi_square_2x2_p(table: list[list[int]]) -> float | None:
    a, b = table[0]
    c, d = table[1]
    n = a + b + c + d
    if n == 0:
        return None
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    if denom == 0:
        return None
    chi2 = n * (a * d - b * c) ** 2 / denom
    return math.erfc(math.sqrt(chi2 / 2.0))


def load_status(input_dir: Path) -> list[dict[str, Any]]:
    status_dir = input_dir / "status"
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(status_dir.glob("*.jsonl")):
        for row in read_jsonl(path):
            if row.get("cell_key"):
                rows[str(row["cell_key"])] = row
    return list(rows.values())


def load_all_status(input_dir: Path) -> list[dict[str, Any]]:
    status_dir = input_dir / "status"
    rows: list[dict[str, Any]] = []
    for path in sorted(status_dir.glob("*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def load_raw(input_dir: Path) -> list[dict[str, Any]]:
    raw_dir = input_dir / "raw"
    rows: list[dict[str, Any]] = []
    for path in sorted(raw_dir.glob("*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def load_metadata(input_dir: Path) -> dict[str, Any]:
    meta_path = input_dir / "metadata" / "real_case_smoke_run_metadata.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {}


def summarize_subset(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in rows if r.get("status") == "ok"]
    success = sum(1 for r in ok if r.get("mutation_success") is True)
    hidden = sum(1 for r in ok if r.get("hidden_business_rule_violation") is True)
    visible = sum(1 for r in ok if r.get("visible_rule_exposed") is True or r.get("visible_policy_error") is True)
    recovery_success = sum(1 for r in ok if r.get("recovery_success") is True)
    oracle_ok = sum(1 for r in ok if r.get("deterministic_oracle_ok") is True)
    return {
        "planned_or_observed_n": len(rows),
        "ok_n": len(ok),
        "status_counts": dict(Counter(str(r.get("status")) for r in rows)),
        "success_n": success,
        "success_rate": rate(success, len(ok)),
        "hidden_violation_n": hidden,
        "hidden_violation_rate": rate(hidden, len(ok)),
        "visible_rule_exposed_n": visible,
        "visible_rule_exposed_rate": rate(visible, len(ok)),
        "recovery_success_n": recovery_success,
        "recovery_success_rate": rate(recovery_success, len(ok)),
        "deterministic_oracle_ok_n": oracle_ok,
        "deterministic_oracle_ok_rate": rate(oracle_ok, len(ok)),
    }


def nested_summary(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for value in sorted({str(r.get(field)) for r in rows}):
        out[value] = {}
        subset = [r for r in rows if str(r.get(field)) == value]
        for cond in CONDITIONS:
            out[value][cond] = summarize_subset([r for r in subset if r.get("condition") == cond])
    return out


def condition_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {cond: summarize_subset([r for r in rows if r.get("condition") == cond]) for cond in CONDITIONS}


def build_statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok_by_cond = {cond: [r for r in rows if r.get("condition") == cond and r.get("status") == "ok"] for cond in CONDITIONS}
    stats: dict[str, Any] = {
        "bootstrap_success_rates": {},
        "bootstrap_hidden_violation_rates": {},
        "bootstrap_success_differences": {},
        "bootstrap_hidden_violation_differences": {},
        "tests_success": {},
        "tests_hidden_violation": {},
    }
    for i, cond in enumerate(CONDITIONS):
        stats["bootstrap_success_rates"][cond] = bootstrap_mean(
            [success_value(r) for r in ok_by_cond[cond]], BOOTSTRAP_SEED + i
        )
        stats["bootstrap_hidden_violation_rates"][cond] = bootstrap_mean(
            [hidden_value(r) for r in ok_by_cond[cond]], BOOTSTRAP_SEED + 100 + i
        )
    for i, (label, (a_cond, b_cond)) in enumerate(COMPARISONS.items()):
        a_success = [success_value(r) for r in ok_by_cond[a_cond]]
        b_success = [success_value(r) for r in ok_by_cond[b_cond]]
        a_hidden = [hidden_value(r) for r in ok_by_cond[a_cond]]
        b_hidden = [hidden_value(r) for r in ok_by_cond[b_cond]]
        stats["bootstrap_success_differences"][label] = bootstrap_diff(a_success, b_success, BOOTSTRAP_SEED + 200 + i)
        stats["bootstrap_hidden_violation_differences"][label] = bootstrap_diff(a_hidden, b_hidden, BOOTSTRAP_SEED + 300 + i)

        a_s = int(sum(a_success))
        b_s = int(sum(b_success))
        success_table = [[a_s, len(a_success) - a_s], [b_s, len(b_success) - b_s]]
        a_h = int(sum(a_hidden))
        b_h = int(sum(b_hidden))
        hidden_table = [[a_h, len(a_hidden) - a_h], [b_h, len(b_hidden) - b_h]]
        stats["tests_success"][label] = {
            "table": success_table,
            "fisher_p": fisher_two_sided(success_table),
            "chi_square_p": chi_square_2x2_p(success_table),
        }
        stats["tests_hidden_violation"][label] = {
            "table": hidden_table,
            "fisher_p": fisher_two_sided(hidden_table),
            "chi_square_p": chi_square_2x2_p(hidden_table),
        }
    return stats


def formal_recommended(summary: dict[str, Any], metadata: dict[str, Any]) -> tuple[bool, str]:
    if metadata.get("stop_reason"):
        return False, f"Smoke stopped early: {metadata.get('stop_reason')}"
    cond = summary["by_condition"]
    baseline = cond["baseline_old_api"]
    silent = cond["evolved_o0_silent"]
    visible = cond["evolved_visible_feedback"]
    if baseline["ok_n"] == 0 or silent["ok_n"] == 0 or visible["ok_n"] == 0:
        return False, "Insufficient ok rows in one or more conditions."
    if baseline["success_n"] == 0:
        return False, "Baseline old API did not establish a successful task."
    if silent["hidden_violation_n"] == 0:
        return False, "Silent evolved condition did not show hidden semantic violation in smoke."
    if (visible["success_rate"] or 0.0) <= (silent["success_rate"] or 0.0):
        return False, "Visible-feedback condition did not improve over silent condition."
    return True, "Smoke shows baseline success, silent hidden violation, and visible-feedback recovery; Phase 10F is recommended."


def build_summary(input_dir: Path, plan_path: Path) -> dict[str, Any]:
    plan = read_jsonl(plan_path)
    rows = load_status(input_dir)
    all_status_rows = load_all_status(input_dir)
    raw = load_raw(input_dir)
    metadata = load_metadata(input_dir)
    selected_cases = sorted({str(r.get("case_id")) for r in plan})
    status_counts = dict(Counter(str(r.get("status")) for r in rows))
    ok_rows = [r for r in rows if r.get("status") == "ok"]
    summary: dict[str, Any] = {
        "phase": "phase10e",
        "input_dir": str(input_dir.relative_to(ROOT)) if input_dir.is_relative_to(ROOT) else str(input_dir),
        "plan_path": str(plan_path.relative_to(ROOT)) if plan_path.is_relative_to(ROOT) else str(plan_path),
        "selected_cases": selected_cases,
        "planned_cells": len(plan),
        "run_cells": len(rows),
        "all_status_records": len(all_status_rows),
        "all_status_record_counts": dict(Counter(str(r.get("status")) for r in all_status_rows)),
        "raw_records": len(raw),
        "status_counts": status_counts,
        "by_condition": condition_summary(rows),
        "by_case": nested_summary(rows, "case_id"),
        "by_model": nested_summary(rows, "model"),
        "by_seed": nested_summary(rows, "seed"),
        "statistics": build_statistics(rows),
        "rule_leakage_rows": [
            r.get("cell_key") for r in rows if r.get("rule_leakage_detected") is True
        ],
        "real_third_party_api_call_rows": [
            r.get("cell_key") for r in rows if r.get("real_third_party_api_call_attempted") is True
        ],
        "deterministic_oracle_worked": None
        if not ok_rows
        else all(r.get("deterministic_oracle_ok") is True for r in ok_rows),
        "provider_error_timeout_failed_not_counted_as_agent_failures": True,
        "metadata": metadata,
    }
    rec, reason = formal_recommended(summary, metadata)
    summary["phase10f_recommended"] = rec
    summary["phase10f_recommendation_reason"] = reason
    return summary


def condition_line(name: str, row: dict[str, Any]) -> str:
    return (
        f"| {name} | {row['ok_n']} | {row['success_n']}/{row['ok_n']} ({pct(row['success_rate'])}) | "
        f"{row['hidden_violation_n']}/{row['ok_n']} ({pct(row['hidden_violation_rate'])}) | "
        f"{row['visible_rule_exposed_n']}/{row['ok_n']} ({pct(row['visible_rule_exposed_rate'])}) | "
        f"{row['status_counts']} |"
    )


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Phase 10E Real-Case Replay Smoke Summary",
        "",
        f"- Selected cases: {', '.join(summary['selected_cases'])}",
        f"- Cells planned: {summary['planned_cells']}",
        f"- Cells with latest terminal status: {summary['run_cells']}",
        "- Latest-cell status counts: " + ", ".join(f"{k}={v}" for k, v in sorted(summary["status_counts"].items())),
        f"- All status records retained: {summary['all_status_records']} ({summary['all_status_record_counts']})",
        f"- Raw records retained: {summary['raw_records']}",
        f"- Deterministic oracle worked for ok rows: {summary['deterministic_oracle_worked'] if summary['deterministic_oracle_worked'] is not None else 'n/a'}",
        f"- Rule leakage rows: {len(summary['rule_leakage_rows'])}",
        f"- Real third-party API call rows: {len(summary['real_third_party_api_call_rows'])}",
        f"- Phase 10F recommended: {summary['phase10f_recommended']} ({summary['phase10f_recommendation_reason']})",
        "",
        "## By Condition",
        "",
        "| condition | ok N | success | hidden violation | visible rule exposed | status counts |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for cond in CONDITIONS:
        lines.append(condition_line(cond, summary["by_condition"][cond]))
    lines.extend(
        [
            "",
            "## By Case",
            "",
        ]
    )
    for case_id, conds in summary["by_case"].items():
        lines.append(f"### {case_id}")
        lines.append("")
        lines.append("| condition | ok N | success | hidden violation | visible rule exposed | status counts |")
        lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
        for cond in CONDITIONS:
            lines.append(condition_line(cond, conds[cond]))
        lines.append("")
    lines.extend(["## By Model", ""])
    for model, conds in summary["by_model"].items():
        lines.append(f"### {model}")
        lines.append("")
        lines.append("| condition | ok N | success | hidden violation | visible rule exposed | status counts |")
        lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
        for cond in CONDITIONS:
            lines.append(condition_line(cond, conds[cond]))
        lines.append("")
    lines.extend(["## By Seed", ""])
    for seed, conds in summary["by_seed"].items():
        lines.append(f"### seed={seed}")
        lines.append("")
        lines.append("| condition | ok N | success | hidden violation | visible rule exposed | status counts |")
        lines.append("| --- | ---: | ---: | ---: | ---: | --- |")
        for cond in CONDITIONS:
            lines.append(condition_line(cond, conds[cond]))
        lines.append("")
    stats = summary["statistics"]
    lines.extend(
        [
            "## Statistical Checks",
            "",
            "Bootstrap success-rate CIs:",
        ]
    )
    for cond, item in stats["bootstrap_success_rates"].items():
        lines.append(
            f"- {cond}: {pct(item['point'])} CI [{pct(item['ci95']['lo'])}, {pct(item['ci95']['hi'])}], n={item['n']}"
        )
    lines.extend(["", "Bootstrap success-rate differences:"])
    for label, item in stats["bootstrap_success_differences"].items():
        lines.append(
            f"- {label}: {pct(item['point'])} CI [{pct(item['ci95']['lo'])}, {pct(item['ci95']['hi'])}]"
        )
    lines.extend(["", "Bootstrap hidden-violation-rate differences:"])
    for label, item in stats["bootstrap_hidden_violation_differences"].items():
        lines.append(
            f"- {label}: {pct(item['point'])} CI [{pct(item['ci95']['lo'])}, {pct(item['ci95']['hi'])}]"
        )
    lines.extend(["", "Fisher exact / chi-square tests on success:"])
    for label, item in stats["tests_success"].items():
        lines.append(
            f"- {label}: Fisher p={fmt_p(item['fisher_p'])}, chi-square p={fmt_p(item['chi_square_p'])}, table={item['table']}"
        )
    lines.extend(["", "Fisher exact / chi-square tests on hidden violations:"])
    for label, item in stats["tests_hidden_violation"].items():
        lines.append(
            f"- {label}: Fisher p={fmt_p(item['fisher_p'])}, chi-square p={fmt_p(item['chi_square_p'])}, table={item['table']}"
        )
    lines.extend(
        [
            "## Integrity Notes",
            "",
            "- No real Stripe/GitHub/other third-party API calls are made by the local replay wrapper.",
            "- Provider_error/timeout/failed rows are not counted as agent failures.",
            "- This is a smoke result, not a formal paper result.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def load_audit() -> dict[str, Any]:
    if AUDIT_JSON.exists():
        return json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    return {}


def wrapper_design_from_plan(plan_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in plan_rows:
        case_id = str(row.get("case_id"))
        if case_id not in out:
            out[case_id] = {
                "old_semantics": row.get("old_semantics"),
                "new_semantics": row.get("new_semantics"),
                "schema_unchanged": row.get("schema_changed") is False,
                "o0_silent_behavior": row.get("evolved_o0_behavior"),
                "visible_feedback_behavior": row.get("visible_feedback_behavior"),
                "deterministic_oracle": row.get("oracle_rule"),
            }
    return out


def write_report(path: Path, summary: dict[str, Any], plan_path: Path) -> None:
    audit = load_audit()
    plan = read_jsonl(plan_path)
    design = wrapper_design_from_plan(plan)
    audit_rows = audit.get("audit_rows", [])
    cond = summary["by_condition"]
    lines = [
        "# Phase 10E Real-Changelog-Grounded Case Replay Smoke Report",
        "",
        "## 1. Executive Summary",
        "",
        f"- Cases audited: {len(audit_rows)}.",
        f"- Cases selected: {', '.join(summary['selected_cases'])}.",
        f"- Smoke run status: {summary['metadata'].get('status', 'unknown')}; stop reason: {summary['metadata'].get('stop_reason')}.",
        "- Status counts: " + ", ".join(f"{k}={v}" for k, v in sorted(summary["status_counts"].items())),
        f"- All status records retained: {summary['all_status_records']} ({summary['all_status_record_counts']}).",
        f"- Raw records retained: {summary['raw_records']}.",
        (
            "- Headline smoke pattern: "
            f"baseline success {cond['baseline_old_api']['success_n']}/{cond['baseline_old_api']['ok_n']}, "
            f"silent hidden violation {cond['evolved_o0_silent']['hidden_violation_n']}/{cond['evolved_o0_silent']['ok_n']}, "
            f"visible recovery success {cond['evolved_visible_feedback']['success_n']}/{cond['evolved_visible_feedback']['ok_n']}."
        ),
        f"- Formal Phase 10F recommended: {summary['phase10f_recommended']} ({summary['phase10f_recommendation_reason']})",
        "",
        "## 2. Case Audit",
        "",
        "| case | provider | class | evidence | wrapper feasible | oracle feasible | smoke | risks |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in audit_rows:
        lines.append(
            f"| {row.get('case_id')} | {row.get('provider')} | {row.get('taxonomy_class')} | "
            f"{row.get('evidence_snippet_exists')} | {row.get('deterministic_wrapper_possible')} | "
            f"{row.get('deterministic_oracle_possible')} | {row.get('suitable_for_smoke')} | {row.get('risks')} |"
        )
    lines.extend(["", "## 3. Wrapper Design", ""])
    for case_id, row in design.items():
        lines.extend(
            [
                f"### {case_id}",
                "",
                f"- Old semantics: {row['old_semantics']}",
                f"- New semantics: {row['new_semantics']}",
                f"- Schema unchanged aspect: {row['schema_unchanged']}",
                f"- O0 silent behavior: {row['o0_silent_behavior']}",
                f"- Visible feedback behavior: {row['visible_feedback_behavior']}",
                f"- Deterministic oracle: {row['deterministic_oracle']}",
                "",
            ]
        )
    lines.extend(
        [
            "## 4. Smoke Results",
            "",
            "| condition | ok N | success | hidden violation | visible rule exposed | status counts |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for condition in CONDITIONS:
        lines.append(condition_line(condition, cond[condition]))
    lines.extend(
        [
            "",
            "Case-level and model-level breakdowns are in `smoke/real_case_smoke_summary.json` and `smoke/real_case_smoke_summary.md`.",
            "",
            "## 5. Integrity",
            "",
            "- No real third-party API calls were made by the deterministic wrappers.",
            "- No rule leakage is allowed in baseline_old_api or evolved_o0_silent prompts; runner preflight checks this.",
            "- Provider_error/timeout/failed rows are not counted as agent failures.",
            "- No paper body files were edited.",
            "- Frozen main results and Phase 5/8 outputs were not modified by this stage.",
            "",
            "## 6. Recommendation for Phase 10F",
            "",
        ]
    )
    if summary["phase10f_recommended"]:
        n_cases = len(summary["selected_cases"])
        n_models = len({r.get("model") for r in plan})
        suggested_seeds = 3
        expected = n_cases * n_models * len(CONDITIONS) * suggested_seeds
        lines.extend(
            [
                "- Run formal: yes.",
                f"- Cases: {', '.join(summary['selected_cases'])}.",
                f"- Models: keep the {n_models} smoke models if provider stability remains acceptable.",
                f"- Seeds: {suggested_seeds}.",
                f"- Expected cells: {expected}.",
                "- Repairs needed: none for wrapper/oracle; review any provider or parse failures before formalizing.",
            ]
        )
    else:
        lines.extend(
            [
                "- Run formal: no, not until the smoke issue is repaired or rerun.",
                f"- Reason: {summary['phase10f_recommendation_reason']}",
                "- Repairs needed: inspect provider availability, parse failures, or wrapper prompts depending on stop reason.",
            ]
        )
    lines.extend(
        [
            "",
            "## 7. What Not To Claim Yet",
            "",
            "- Do not claim production frequency.",
            "- Do not claim production incident.",
            "- Do not claim formal real-case evidence until Phase 10F.",
            "- Do not merge smoke into paper.",
            "- Do not claim all real API changes behave like these cases.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(args.input_dir, args.plan)
    write_json(args.output_json, summary)
    write_summary_md(args.output_md, summary)
    write_report(args.report_md, summary, args.plan)
    print(
        json.dumps(
            {
                "summary_md": str(args.output_md),
                "summary_json": str(args.output_json),
                "report_md": str(args.report_md),
                "planned_cells": summary["planned_cells"],
                "run_cells": summary["run_cells"],
                "status_counts": summary["status_counts"],
                "phase10f_recommended": summary["phase10f_recommended"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
