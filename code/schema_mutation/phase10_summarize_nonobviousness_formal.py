"""Summarize Phase 10C non-obviousness formal outputs."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent.parent
PHASE10 = ROOT / "runs" / "schema_mutation" / "phase10"
PLAN = PHASE10 / "nonobviousness" / "nonobviousness_control_plan.jsonl"
DEFAULT_OUT = PHASE10 / "phase10c" / "nonobviousness_formal"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def latest_status_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("cell_key") or "")
        if key:
            latest[key] = row
    return latest


def load_status_rows(input_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    status_dir = input_dir / "status"
    if not status_dir.exists():
        return rows
    for path in sorted(status_dir.glob("nonobviousness_[0-9][0-9][0-9][0-9]_status.jsonl")):
        for row in read_jsonl(path):
            row = dict(row)
            row["_status_file"] = path.name
            rows.append(row)
    return rows


def load_metadata(input_dir: Path) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}
    meta_dir = input_dir / "metadata"
    if not meta_dir.exists():
        return metadata
    for path in sorted(meta_dir.glob("nonobviousness_[0-9][0-9][0-9][0-9]_metadata.json")):
        metadata[path.stem.replace("_metadata", "")] = read_json(path)
    return metadata


def status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(row.get("status")) for row in rows))


def group_metrics(
    planned: list[dict[str, Any]],
    latest: dict[str, dict[str, Any]],
    field: str,
) -> dict[str, dict[str, Any]]:
    planned_by_group = Counter(str(row.get(field)) for row in planned)
    rows_by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in latest.values():
        rows_by_group[str(row.get(field))].append(row)
    metrics: dict[str, dict[str, Any]] = {}
    for group in sorted(planned_by_group):
        rows = rows_by_group.get(group, [])
        ok_rows = [row for row in rows if row.get("status") == "ok"]
        success_n = sum(1 for row in ok_rows if row.get("mutation_success") is True or float(row.get("reward") or 0) > 0)
        hidden_n = sum(1 for row in ok_rows if row.get("hidden_business_rule_violation") is True)
        visible_n = sum(1 for row in ok_rows if row.get("visible_policy_error") is True)
        migration_n = sum(1 for row in ok_rows if row.get("migration_note_visible") is True)
        metrics[group] = {
            "planned": planned_by_group[group],
            "observed": len(rows),
            "missing": planned_by_group[group] - len(rows),
            "status_counts": status_counts(rows),
            "ok": len(ok_rows),
            "success_n": success_n,
            "success_rate": rate(success_n, len(ok_rows)),
            "hidden_violation_n": hidden_n,
            "hidden_violation_rate": rate(hidden_n, len(ok_rows)),
            "visible_policy_error_n": visible_n,
            "visible_policy_error_rate": rate(visible_n, len(ok_rows)),
            "migration_note_visible_n": migration_n,
            "migration_note_visible_rate": rate(migration_n, len(ok_rows)),
        }
    return metrics


def rule_leakage_issues(planned: list[dict[str, Any]], latest: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in planned:
        cond = str(row.get("condition"))
        cell_key = str(row.get("cell_key"))
        variant = str(row.get("agent_prompt_variant") or "")
        level = str(row.get("observability_level") or "")
        drift = str(row.get("business_rule_drift") or "")
        if cond in {"O0_increased_reasoning_budget", "O0_reflection_scaffold"}:
            if variant == "rule_visible_preamble":
                issues.append({"cell_key": cell_key, "issue": "O0 row has rule-visible variant"})
            if level != "O0_silent":
                issues.append({"cell_key": cell_key, "issue": f"O0 row has observability_level={level}"})
            low = drift.lower()
            if "evolved api rule is" in drift or "migration note" in low or "rule-visible" in low:
                issues.append({"cell_key": cell_key, "issue": "O0 drift text appears prompt-like"})
        if cond == "rule_in_tool_preamble_upper_bound":
            if variant != "rule_visible_preamble":
                issues.append({"cell_key": cell_key, "issue": "upper-bound row lacks rule-visible variant"})
            if level != "O4_migration_note":
                issues.append({"cell_key": cell_key, "issue": f"upper-bound row has observability_level={level}"})
    for row in latest.values():
        cond = str(row.get("condition"))
        if cond in {"O0_increased_reasoning_budget", "O0_reflection_scaffold"}:
            if row.get("visible_policy_error") is True:
                issues.append({"cell_key": row.get("cell_key"), "issue": "O0 row exposed visible_policy_error"})
            if row.get("migration_note_visible") is True:
                issues.append({"cell_key": row.get("cell_key"), "issue": "O0 row exposed migration_note"})
    return issues


def summarize(plan_path: Path, input_dir: Path) -> dict[str, Any]:
    planned = read_jsonl(plan_path)
    rows = load_status_rows(input_dir)
    latest = latest_status_rows(rows)
    metadata = load_metadata(input_dir)
    planned_keys = {str(row.get("cell_key")) for row in planned}
    observed_keys = set(latest)
    latest_rows = list(latest.values())
    overall_status = Counter(str(row.get("status")) for row in latest_rows)
    stopped_shards = {
        shard: meta
        for shard, meta in metadata.items()
        if meta.get("status") not in {None, "completed"}
    }
    missing = planned_keys - observed_keys
    extra = observed_keys - planned_keys
    leakage = rule_leakage_issues(planned, latest)
    fake_rows = [row.get("cell_key") for row in latest_rows if row.get("fake_run") is True or row.get("execution_mode") == "local_fake"]
    baseline_false = [row.get("cell_key") for row in latest_rows if row.get("baseline_success") is not True]
    non_ok_rows = [
        {
            "cell_key": row.get("cell_key"),
            "status": row.get("status"),
            "condition": row.get("condition"),
            "model": row.get("model"),
            "env": row.get("env"),
            "semantic_class": row.get("semantic_class"),
            "status_file": row.get("_status_file"),
        }
        for row in latest_rows
        if row.get("status") != "ok"
    ]
    by_condition = group_metrics(planned, latest, "condition")
    upper = by_condition.get("rule_in_tool_preamble_upper_bound", {})
    o0_reason = by_condition.get("O0_increased_reasoning_budget", {})
    o0_refl = by_condition.get("O0_reflection_scaffold", {})
    o0_rates = [
        value
        for value in [o0_reason.get("success_rate"), o0_refl.get("success_rate")]
        if value is not None
    ]
    upper_rate = upper.get("success_rate")
    formal_status_complete = len(missing) == 0 and len(extra) == 0 and not stopped_shards
    all_ok = overall_status.get("ok", 0) == len(planned) and len(latest_rows) == len(planned)
    summary = {
        "planned_cells": len(planned),
        "completed_status_cells": len(observed_keys & planned_keys),
        "ok_cells": overall_status.get("ok", 0),
        "missing_cells": len(missing),
        "extra_status_cells": len(extra),
        "status_counts": dict(overall_status),
        "by_condition": by_condition,
        "by_domain": group_metrics(planned, latest, "env"),
        "by_model": group_metrics(planned, latest, "model"),
        "by_semantic_class": group_metrics(planned, latest, "semantic_class"),
        "metadata_by_shard": metadata,
        "completed_shards": sum(1 for meta in metadata.values() if meta.get("status") == "completed"),
        "stopped_shards": stopped_shards,
        "formal_status_complete": formal_status_complete,
        "formal_all_ok": all_ok,
        "formal_completed_cleanly": formal_status_complete and all_ok and not leakage and not fake_rows and not baseline_false,
        "non_ok_rows": non_ok_rows,
        "retry_needed_cells": len(non_ok_rows),
        "rule_leakage_detected": bool(leakage),
        "rule_leakage_issues": leakage[:50],
        "fake_rows": fake_rows[:50],
        "baseline_success_false_rows": baseline_false[:50],
        "rule_in_prompt_upper_bound_improves": None,
        "o0_reasoning_reflection_still_struggles": None,
        "phase10d_analysis_ready": formal_status_complete and not stopped_shards and not leakage and not fake_rows and not baseline_false,
        "phase10d_caveat": "exclude or retry non-ok infrastructure rows before final statistical claims"
        if non_ok_rows
        else "all formal rows ok",
    }
    if upper_rate is not None and o0_reason.get("success_rate") is not None:
        summary["rule_in_prompt_upper_bound_improves"] = bool(upper_rate > (o0_reason.get("success_rate") or 0))
    if o0_rates and upper_rate is not None:
        summary["o0_reasoning_reflection_still_struggles"] = bool(max(o0_rates) < upper_rate)
    return summary


def table_lines(title: str, rows: dict[str, dict[str, Any]]) -> list[str]:
    lines = [
        f"## {title}",
        "",
        "| group | planned | completed | ok | status counts | success | hidden violation | visible policy error |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for group, row in sorted(rows.items()):
        counts = ", ".join(f"{k}={v}" for k, v in sorted(row["status_counts"].items())) or "none"
        lines.append(
            f"| {group} | {row['planned']} | {row['observed']} | {row['ok']} | {counts} | "
            f"{fmt(row['success_rate'])} | {fmt(row['hidden_violation_rate'])} | "
            f"{fmt(row['visible_policy_error_rate'])} |"
        )
    lines.append("")
    return lines


def write_outputs(summary: dict[str, Any], output_json: Path, output_md: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Phase 10C Non-Obviousness Formal Summary",
        "",
        f"- Planned cells: {summary['planned_cells']}",
        f"- Completed status cells: {summary['completed_status_cells']}",
        f"- OK cells: {summary['ok_cells']}",
        f"- Missing cells: {summary['missing_cells']}",
        f"- Extra status cells: {summary['extra_status_cells']}",
        "- Status counts: "
        + (", ".join(f"{k}={v}" for k, v in sorted(summary["status_counts"].items())) or "none"),
        f"- Completed shards: {summary['completed_shards']}",
        f"- Formal status complete: {summary['formal_status_complete']}",
        f"- Formal all OK: {summary['formal_all_ok']}",
        f"- Formal completed cleanly: {summary['formal_completed_cleanly']}",
        f"- Rule leakage detected: {summary['rule_leakage_detected']}",
        f"- Retry-needed cells: {summary['retry_needed_cells']}",
        f"- Phase 10D analysis ready: {summary['phase10d_analysis_ready']}",
        f"- Phase 10D caveat: {summary['phase10d_caveat']}",
        "",
    ]
    lines.extend(table_lines("By Condition", summary["by_condition"]))
    lines.extend(table_lines("By Domain", summary["by_domain"]))
    lines.extend(table_lines("By Model", summary["by_model"]))
    lines.extend(table_lines("By Semantic Class", summary["by_semantic_class"]))
    lines.extend(
        [
            "## Pattern Flags",
            "",
            f"- Rule-in-prompt upper bound improves: {summary['rule_in_prompt_upper_bound_improves']}",
            f"- O0 reasoning/reflection still struggles: {summary['o0_reasoning_reflection_still_struggles']}",
            "",
        ]
    )
    if summary["non_ok_rows"]:
        lines.extend(["## Non-OK Rows", ""])
        for row in summary["non_ok_rows"]:
            lines.append(
                f"- {row['cell_key']}: status={row['status']} condition={row['condition']} "
                f"model={row['model']} env={row['env']} class={row['semantic_class']} file={row['status_file']}"
            )
        lines.append("")
    if summary["rule_leakage_issues"]:
        lines.extend(["## Rule Leakage Issues", ""])
        for issue in summary["rule_leakage_issues"]:
            lines.append(f"- {issue['cell_key']}: {issue['issue']}")
        lines.append("")
    if summary["stopped_shards"]:
        lines.extend(["## Stopped Shards", ""])
        for shard, meta in sorted(summary["stopped_shards"].items()):
            lines.append(f"- {shard}: {meta.get('status')} counts={meta.get('status_counts', {})}")
        lines.append("")
    output_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--plan", default=str(PLAN))
    parser.add_argument("--output-md", default=str(DEFAULT_OUT / "nonobviousness_formal_summary.md"))
    parser.add_argument("--output-json", default=str(DEFAULT_OUT / "nonobviousness_formal_summary.json"))
    args = parser.parse_args()
    summary = summarize(resolve_path(args.plan), resolve_path(args.input_dir))
    write_outputs(summary, resolve_path(args.output_json), resolve_path(args.output_md))
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
