"""Generate Day-16 airline summary and audit artifacts."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from code.schema_mutation.c4_observability_modes import c4_mode_matches

ROOT = Path(__file__).resolve().parent.parent.parent
RUNS = ROOT / "runs" / "schema_mutation"

FILES = {
    "ds_base_s0": RUNS / "day14_airline_baseline_deepseek_t0_9_s0_combined.jsonl",
    "ds_c4a_s0": RUNS / "day15_airline_c4a_deepseek_t0_1_4_5_6_7_s0_exposed_timeout240.jsonl",
    "ds_c4b_s0": RUNS / "day14_airline_c4b_deepseek_t0_9_s0_exposed_combined.jsonl",
    "ds_base_s12": RUNS / "day16_airline_baseline_deepseek_t0_1_4_5_6_7_s12_timeout240.jsonl",
    "ds_c4a_s12": RUNS / "day16_airline_c4a_deepseek_t0_1_4_5_6_7_s12_exposed_timeout240.jsonl",
    "ds_c4b_s12": RUNS / "day16_airline_c4b_deepseek_t0_1_4_5_6_7_s12_exposed_timeout240.jsonl",
    "ds_unused_s0": RUNS / "day16_airline_c4b_deepseek_t0_1_4_5_6_7_s0_unused_timeout240.jsonl",
    "qwen_base": RUNS / "day16_airline_baseline_qwen_max_t0_1_4_5_6_7_s0_timeout240.jsonl",
    "qwen_c4a": RUNS / "day16_airline_c4a_qwen_max_t0_1_4_7_s0_exposed_timeout240.jsonl",
    "qwen_c4b": RUNS / "day16_airline_c4b_qwen_max_t0_1_4_7_s0_exposed_timeout240.jsonl",
}

DEEPSEEK = "deepseek/deepseek-v4-flash"
QWEN = "dashscope/qwen3.7-max-2026-06-08"
TASKS = {0, 1, 4, 5, 6, 7}
QWEN_TASKS = {0, 1, 4, 7}


def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_all() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in FILES.values():
        rows.extend(load_rows(path))
    return rows


def cell_key(r: dict[str, Any]) -> tuple[Any, ...]:
    return (r.get("task_index"), r.get("model"), r.get("seed"))


def reward(r: dict[str, Any]) -> float:
    return float(r.get("reward") or 0.0)


def actions(r: dict[str, Any]) -> list[dict[str, Any]]:
    raw = r.get("raw") or {}
    acts = raw.get("taken_actions") or []
    return [a for a in acts if isinstance(a, dict)]


def action_names(r: dict[str, Any]) -> list[str]:
    return [str(a.get("name")) for a in actions(r)]


def bootstrap_ci(values: list[float], reps: int = 10_000, seed: int = 7) -> tuple[float, float] | None:
    if not values:
        return None
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(reps):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * (reps - 1))]
    hi = means[int(0.975 * (reps - 1))]
    return lo, hi


def fmt_ci(ci: tuple[float, float] | None) -> str:
    if ci is None:
        return "NA"
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def baseline_good(rows: list[dict[str, Any]], model: str, task_set: set[int]) -> dict[tuple[Any, ...], dict[str, Any]]:
    base: dict[tuple[Any, ...], dict[str, Any]] = {}
    for r in rows:
        if not (
            r.get("status") == "ok"
            and r.get("model") == model
            and r.get("mutation_type") is None
            and r.get("task_index") in task_set
        ):
            continue
        base[cell_key(r)] = r
    return {k: r for k, r in base.items() if reward(r) > 0}


def all_baselines(rows: list[dict[str, Any]], model: str, task_set: set[int]) -> dict[tuple[Any, ...], dict[str, Any]]:
    base: dict[tuple[Any, ...], dict[str, Any]] = {}
    for r in rows:
        if (
            r.get("status") == "ok"
            and r.get("model") == model
            and r.get("mutation_type") is None
            and r.get("task_index") in task_set
        ):
            base[cell_key(r)] = r
    return base


def condition_runs(rows: list[dict[str, Any]], model: str, task_set: set[int], mode: str) -> list[dict[str, Any]]:
    return [
        r
        for r in rows
        if r.get("status") == "ok"
        and r.get("model") == model
        and r.get("mutation_type") == "C4_business_rule_drift"
        and r.get("target_policy") == "intent_aligned"
        and c4_mode_matches(r, mode)
        and r.get("task_index") in task_set
    ]


def summarize_condition(rows: list[dict[str, Any]], model: str, task_set: set[int], mode: str) -> dict[str, Any]:
    base = all_baselines(rows, model, task_set)
    good = {k: r for k, r in base.items() if reward(r) > 0}
    runs = condition_runs(rows, model, task_set, mode)
    paired: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for r in runs:
        b = good.get(cell_key(r))
        if b is not None:
            paired.append((r, b))

    n = len(paired)
    success_values = [reward(r) for r, _ in paired]
    return {
        "model": model,
        "mode": mode,
        "all_runs": len(runs),
        "baseline_good": len(good),
        "baseline_total": len(base),
        "paired": n,
        "success": sum(success_values) / n if n else None,
        "success_ci_bootstrap": bootstrap_ci(success_values),
        "drops": sum(1 for r, b in paired if reward(b) > reward(r)),
        "oracle_rule_violation": sum(1 for r, _ in paired if r.get("oracle_rule_violation")),
        "visible_policy_error": sum(1 for r, _ in paired if r.get("visible_policy_error")),
        "hidden_business_rule_violation": sum(1 for r, _ in paired if r.get("hidden_business_rule_violation")),
        "all_oracle_rule_violation": sum(1 for r in runs if r.get("oracle_rule_violation")),
        "all_visible_policy_error": sum(1 for r in runs if r.get("visible_policy_error")),
        "all_hidden_business_rule_violation": sum(1 for r in runs if r.get("hidden_business_rule_violation")),
        "timeouts": sum(1 for r in runs if r.get("status") == "timeout"),
        "max_actions": sum(1 for r in runs if int(r.get("num_actions") or 0) >= 30),
    }


def summarize_unused_control(rows: list[dict[str, Any]]) -> dict[str, Any]:
    good = baseline_good(rows, DEEPSEEK, TASKS)
    runs = [
        r
        for r in rows
        if r.get("status") == "ok"
        and r.get("model") == DEEPSEEK
        and r.get("mutation_type") == "C4_business_rule_drift"
        and r.get("target_policy") == "unused_tool"
        and c4_mode_matches(r, "silent")
        and r.get("task_index") in TASKS
    ]
    paired = [(r, good[cell_key(r)]) for r in runs if cell_key(r) in good]
    values = [reward(r) for r, _ in paired]
    return {
        "condition": "C4b unused_tool",
        "paired": len(paired),
        "success": sum(values) / len(values) if values else None,
        "success_ci_bootstrap": bootstrap_ci(values),
        "oracle_rule_violation": sum(1 for r, _ in paired if r.get("oracle_rule_violation")),
        "visible_policy_error": sum(1 for r, _ in paired if r.get("visible_policy_error")),
        "hidden_business_rule_violation": sum(1 for r, _ in paired if r.get("hidden_business_rule_violation")),
        "drops": sum(1 for r, b in paired if reward(b) > reward(r)),
    }


def summarize_audit(rows: list[dict[str, Any]], model: str, task_set: set[int]) -> dict[str, Any]:
    runs = condition_runs(rows, model, task_set, "silent")
    target_miss = 0
    for r in runs:
        tool = r.get("mutation_tool")
        if tool and tool not in action_names(r):
            target_miss += 1
    return {
        "model": model,
        "c4b_runs": len(runs),
        "timeouts": sum(1 for r in runs if r.get("status") == "timeout"),
        "max_step_cutoff": sum(1 for r in runs if int(r.get("num_actions") or 0) >= 30),
        "target_tool_not_called": target_miss,
        "visible_policy_error": sum(1 for r in runs if r.get("visible_policy_error")),
        "hidden_business_rule_violation": sum(1 for r in runs if r.get("hidden_business_rule_violation")),
        "nonzero_reward": sum(1 for r in runs if reward(r) > 0),
    }


def find_record(
    rows: list[dict[str, Any]],
    model: str,
    task: int,
    seed: int,
    mode: str | None,
    target_policy: str = "intent_aligned",
) -> dict[str, Any] | None:
    for r in rows:
        if r.get("model") != model or r.get("task_index") != task or r.get("seed") != seed:
            continue
        if mode is None:
            if r.get("mutation_type") is None:
                return r
        elif (
            r.get("mutation_type") == "C4_business_rule_drift"
            and c4_mode_matches(r, mode)
            and r.get("target_policy") == target_policy
        ):
            return r
    return None


def audit_case(
    rows: list[dict[str, Any]],
    label: str,
    model: str,
    task: int,
    seed: int,
    mode: str | None,
    target_policy: str = "intent_aligned",
) -> dict[str, Any]:
    r = find_record(rows, model, task, seed, mode, target_policy)
    if r is None:
        return {"label": label, "missing": True}
    base = find_record(rows, model, task, seed, None)
    names = action_names(r)
    tool = r.get("mutation_tool")
    meta = r.get("mutation_meta") or {}
    return {
        "label": label,
        "model": model,
        "task": task,
        "seed": seed,
        "status": r.get("status"),
        "baseline_reward": reward(base) if base else None,
        "mutation_reward": reward(r),
        "target_policy": r.get("target_policy"),
        "c4_runtime_mode": r.get("c4_runtime_mode"),
        "mutation_tool": tool,
        "target_tool_called": tool in names if tool else None,
        "target_tool_call_count": names.count(tool) if tool else 0,
        "oracle_rule_violation": bool(r.get("oracle_rule_violation")),
        "visible_policy_error": bool(r.get("visible_policy_error")),
        "hidden_business_rule_violation": bool(r.get("hidden_business_rule_violation")),
        "num_actions": r.get("num_actions"),
        "hit_max_actions": int(r.get("num_actions") or 0) >= 30,
        "wallclock_s": r.get("wallclock_s"),
        "schema_signature_changed": bool(meta.get("param_remap")),
        "mutation_note": r.get("mutation_note"),
        "oracle_rule_error": r.get("oracle_rule_error"),
        "last_actions": names[-8:],
    }


def fmt_success(value: float | None) -> str:
    return "NA" if value is None else f"{value:.3f}"


def main() -> int:
    rows = load_all()
    summaries = [
        summarize_condition(rows, DEEPSEEK, TASKS, "visible"),
        summarize_condition(rows, DEEPSEEK, TASKS, "silent"),
        summarize_condition(rows, QWEN, QWEN_TASKS, "visible"),
        summarize_condition(rows, QWEN, QWEN_TASKS, "silent"),
    ]
    unused = summarize_unused_control(rows)
    audit_summaries = [
        summarize_audit(rows, DEEPSEEK, TASKS),
        summarize_audit(rows, QWEN, QWEN_TASKS),
    ]
    audits = [
        audit_case(rows, "DeepSeek C4b silent booking", DEEPSEEK, 0, 0, "silent"),
        audit_case(rows, "DeepSeek C4b silent passenger update", DEEPSEEK, 4, 1, "silent"),
        audit_case(rows, "Qwen C4b silent flight change", QWEN, 7, 0, "silent"),
        audit_case(rows, "DeepSeek unused_tool task7 anomaly", DEEPSEEK, 7, 0, "silent", target_policy="unused_tool"),
    ]

    out_json = RUNS / "day16_airline_final_summary.json"
    out_json.write_text(
        json.dumps(
            {
                "summaries": summaries,
                "unused_control": unused,
                "audit_summaries": audit_summaries,
                "audits": audits,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    lines: list[str] = []
    lines.append("# Day 16 Airline External Validity Summary")
    lines.append("")
    lines.append("## Final paired results")
    lines.append("")
    lines.append(
        "| env | model | condition | all runs | baseline-good | paired | success | bootstrap 95% CI | drops | oracle violation | visible error | hidden violation |"
    )
    lines.append("|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|")
    for s in summaries:
        condition = "C4a visible" if s["mode"] == "visible" else "C4b silent"
        lines.append(
            f"| airline | {s['model']} | {condition} | {s['all_runs']} | "
            f"{s['baseline_good']}/{s['baseline_total']} | {s['paired']} | "
            f"{fmt_success(s['success'])} | {fmt_ci(s['success_ci_bootstrap'])} | "
            f"{s['drops']}/{s['paired']} | {s['oracle_rule_violation']}/{s['paired']} | "
            f"{s['visible_policy_error']}/{s['paired']} | "
            f"{s['hidden_business_rule_violation']}/{s['paired']} |"
        )
    lines.append("")
    lines.append(
        "Note: `all runs` includes every executed C4 run; `paired` filters to baseline-successful cells. "
        "For DeepSeek C4b, all 18/18 runs triggered hidden rule violations, while 17/17 baseline-successful paired runs regressed."
    )
    lines.append("")
    lines.append("## Negative control")
    lines.append("")
    lines.append("| condition | paired | success | bootstrap 95% CI | drops | oracle violation | visible error | hidden violation | interpretation |")
    lines.append("|---|---:|---:|---|---:|---:|---:|---:|---|")
    lines.append(
        f"| {unused['condition']} | {unused['paired']} | {fmt_success(unused['success'])} | "
        f"{fmt_ci(unused['success_ci_bootstrap'])} | {unused['drops']}/{unused['paired']} | "
        f"{unused['oracle_rule_violation']}/{unused['paired']} | "
        f"{unused['visible_policy_error']}/{unused['paired']} | "
        f"{unused['hidden_business_rule_violation']}/{unused['paired']} | "
        "wrapper does not globally break the environment |"
    )
    lines.append("")
    lines.append("## Audit summary")
    lines.append("")
    lines.append("| model | C4b runs | timeout | max-step cutoff | target tool not called | visible error | hidden violation | nonzero reward |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for a in audit_summaries:
        lines.append(
            f"| {a['model']} | {a['c4b_runs']} | {a['timeouts']} | "
            f"{a['max_step_cutoff']} | {a['target_tool_not_called']} | "
            f"{a['visible_policy_error']} | {a['hidden_business_rule_violation']} | {a['nonzero_reward']} |"
        )
    lines.append("")
    lines.append("## Audit cases")
    lines.append("")
    lines.append(
        "| case | model | task | seed | condition | baseline reward | mutation reward | target tool | called? | oracle | visible | hidden | schema signature changed? | max actions? | last actions |"
    )
    lines.append("|---|---|---:|---:|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|")
    for a in audits:
        lines.append(
            f"| {a.get('label')} | {a.get('model')} | {a.get('task')} | {a.get('seed')} | "
            f"{a.get('target_policy')}/{a.get('c4_runtime_mode')} | {a.get('baseline_reward')} | "
            f"{a.get('mutation_reward')} | {a.get('mutation_tool')} | {a.get('target_tool_called')} | "
            f"{a.get('oracle_rule_violation')} | {a.get('visible_policy_error')} | "
            f"{a.get('hidden_business_rule_violation')} | {a.get('schema_signature_changed')} | "
            f"{a.get('hit_max_actions')} | {' → '.join(a.get('last_actions') or [])} |"
        )
    lines.append("")
    lines.append("## Representative C4b case study")
    lines.append("")
    case = audits[0]
    lines.append(
        f"In `{case['label']}` (task {case['task']}, seed {case['seed']}), the baseline trajectory succeeds "
        f"with reward {case['baseline_reward']}. The C4b mutation keeps the call signature schema-compatible "
        f"(`schema_signature_changed={case['schema_signature_changed']}`) but silently changes the business rule on "
        f"`{case['mutation_tool']}`. The agent still calls the target tool "
        f"{case['target_tool_call_count']} time(s), receives no visible policy error "
        f"(`visible_policy_error={case['visible_policy_error']}`), and terminates without max-step cutoff "
        f"(`hit_max_actions={case['hit_max_actions']}`). The hidden oracle marks the business-rule violation "
        f"(`hidden_business_rule_violation={case['hidden_business_rule_violation']}`), producing reward "
        f"{case['mutation_reward']}. This illustrates the core failure mode: a typed client and the agent's API call remain valid, "
        "but the old business assumption is no longer valid under the evolved API semantics."
    )
    lines.append("")
    lines.append("## Key takeaway")
    lines.append("")
    lines.append(
        "C4a and C4b instantiate the same semantic API evolution but differ in observability. "
        "Visible policy errors give agents a chance to revise their plans; silent business-rule drift leaves the "
        "schema and call signature valid while exposing no actionable error. Across DeepSeek multi-seed and Qwen-max "
        "second-model airline replications, this observability gap produces systematic agent-facing compatibility failures."
    )

    out_md = RUNS / "day16_airline_final_summary.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out_json}")
    print(f"wrote {out_md}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
