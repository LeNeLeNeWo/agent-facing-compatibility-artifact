"""Summarize Phase 10B non-obviousness smoke output."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent.parent
PHASE10 = ROOT / "runs" / "schema_mutation" / "phase10"
OUT = PHASE10 / "phase10b" / "nonobviousness_smoke"
SHARD = PHASE10 / "nonobviousness" / "shards" / "nonobviousness_smoke.jsonl"
RESULTS = OUT / "smoke_results.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def rate(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def summarize() -> dict[str, Any]:
    planned = read_jsonl(SHARD)
    rows = read_jsonl(RESULTS)
    metadata_path = OUT / "smoke_run_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    by_condition_planned = Counter(str(row.get("condition")) for row in planned)
    by_condition_status: dict[str, Counter[str]] = defaultdict(Counter)
    metrics: dict[str, dict[str, Any]] = {}
    for row in rows:
        cond = str(row.get("condition"))
        by_condition_status[cond][str(row.get("status"))] += 1
    for cond in sorted(by_condition_planned):
        ok_rows = [row for row in rows if row.get("condition") == cond and row.get("status") == "ok"]
        success_n = sum(1 for row in ok_rows if row.get("mutation_success") is True or float(row.get("reward") or 0) > 0)
        hidden_n = sum(1 for row in ok_rows if row.get("hidden_business_rule_violation") is True)
        metrics[cond] = {
            "planned": by_condition_planned[cond],
            "status_counts": dict(by_condition_status.get(cond, Counter())),
            "ok": len(ok_rows),
            "success_n": success_n,
            "success_rate": rate(success_n, len(ok_rows)),
            "hidden_violation_n": hidden_n,
            "hidden_violation_rate": rate(hidden_n, len(ok_rows)),
        }
    upper = metrics.get("rule_in_tool_preamble_upper_bound", {})
    o0_reason = metrics.get("O0_increased_reasoning_budget", {})
    o0_refl = metrics.get("O0_reflection_scaffold", {})
    summary = {
        "planned_smoke_cells": len(planned),
        "actually_run_cells": sum(1 for row in rows if row.get("status") not in {"not_run", "skipped"}),
        "status_counts": dict(Counter(str(row.get("status")) for row in rows)),
        "planned_by_condition": dict(by_condition_planned),
        "by_condition": metrics,
        "metadata": metadata,
        "rule_in_prompt_upper_bound_improves": None,
        "o0_reasoning_reflection_still_struggles": None,
        "formal_phase10c_recommended": None,
    }
    if upper.get("ok") and o0_reason.get("ok"):
        summary["rule_in_prompt_upper_bound_improves"] = bool(
            (upper.get("success_rate") or 0) > (o0_reason.get("success_rate") or 0)
        )
    if o0_reason.get("ok") or o0_refl.get("ok"):
        o0_rates = [
            value
            for value in [o0_reason.get("success_rate"), o0_refl.get("success_rate")]
            if value is not None
        ]
        upper_rate = upper.get("success_rate")
        if o0_rates and upper_rate is not None:
            summary["o0_reasoning_reflection_still_struggles"] = bool(max(o0_rates) < upper_rate)
    summary["formal_phase10c_recommended"] = bool(
        summary["actually_run_cells"] > 0
        and not any(summary["status_counts"].get(k, 0) >= 3 for k in ("provider_error", "timeout", "failed"))
    )
    return summary


def write_outputs(summary: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "smoke_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Phase 10B Non-Obviousness Smoke Summary",
        "",
        f"- Planned smoke cells: {summary['planned_smoke_cells']}",
        f"- Actually run cells: {summary['actually_run_cells']}",
        "- Status counts: "
        + (", ".join(f"{k}={v}" for k, v in sorted(summary["status_counts"].items())) or "none"),
        f"- Runner status: {summary.get('metadata', {}).get('status', 'unknown')}",
        "",
        "## By Condition",
        "",
        "| condition | planned | ok | status counts | success | hidden violation |",
        "| --- | ---: | ---: | --- | ---: | ---: |",
    ]
    for cond, row in sorted(summary["by_condition"].items()):
        counts = ", ".join(f"{k}={v}" for k, v in sorted(row["status_counts"].items())) or "none"
        lines.append(
            f"| {cond} | {row['planned']} | {row['ok']} | {counts} | "
            f"{fmt(row['success_rate'])} | {fmt(row['hidden_violation_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Preliminary Pattern",
            "",
        ]
    )
    if summary["actually_run_cells"] == 0:
        issues = summary.get("metadata", {}).get("issues", [])
        lines.append(
            "Smoke did not execute agent calls because preflight stopped the run. "
            "This is an infrastructure readiness result, not a scientific result."
        )
        if issues:
            lines.append("")
            lines.append("Preflight issues:")
            for issue in issues:
                lines.append(f"- {issue}")
    else:
        lines.append(
            "Smoke executed at least one cell. Treat all success and hidden-violation rates as pipeline smoke evidence only, not as final experimental conclusions."
        )
    lines.extend(
        [
            "",
            f"- Rule-in-prompt upper bound improves: {summary['rule_in_prompt_upper_bound_improves']}",
            f"- O0 reasoning/reflection still struggles: {summary['o0_reasoning_reflection_still_struggles']}",
            f"- Formal Phase 10C recommended: {summary['formal_phase10c_recommended']}",
            "",
        ]
    )
    (OUT / "smoke_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    summary = summarize()
    write_outputs(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
