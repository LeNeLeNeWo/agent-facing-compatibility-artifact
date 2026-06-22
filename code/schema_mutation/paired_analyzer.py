"""Paired analysis for schema-mutation pilots.

Matches mutation records to baseline records by (task_index, model, seed), then
reports per-record and per-task deltas.

Example:
    python -m code.schema_mutation.paired_analyzer \
      --baseline runs/schema_mutation/day6_mutation_on_good_deepseek.jsonl \
      --mutations used=runs/schema_mutation/day9_runtime_c4_fixed_used.jsonl \
                  unused=runs/schema_mutation/day9_runtime_c4_fixed_unused.jsonl
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any


def _load_latest(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    latest: dict[tuple[Any, ...], dict[str, Any]] = {}
    for r in rows:
        key = (
            r.get("task_index"),
            r.get("model"),
            r.get("mutation_type"),
            r.get("seed"),
            r.get("env_user_model"),
            r.get("env_user_provider"),
            r.get("temperature"),
            r.get("target_policy", "random"),
            r.get("observability_level"),
        )
        latest[key] = r
    return list(latest.values())


def _base_key(r: dict[str, Any]) -> tuple[Any, ...]:
    return (r.get("task_index"), r.get("model"), r.get("seed"))


def _reward(r: dict[str, Any]) -> float:
    return float(r.get("reward") or 0.0)


def _num_actions(r: dict[str, Any]) -> int:
    return int(r.get("num_actions") or 0)


def _oracle_rule_violation(r: dict[str, Any]) -> bool:
    if "oracle_rule_violation" in r:
        return bool(r.get("oracle_rule_violation"))
    return bool(r.get("runtime_policy_violation"))


def _visible_policy_error(r: dict[str, Any]) -> bool:
    if r.get("visible_policy_error") is not None:
        return bool(r.get("visible_policy_error"))
    mode = str(r.get("oracle_rule_mode") or r.get("runtime_policy_mode") or "")
    return bool((r.get("oracle_rule_error") or r.get("runtime_policy_error")) and mode == "visible")



def _rule_mode(r: dict[str, Any]) -> str:
    return str(
        r.get("observability_level")
        or r.get("oracle_rule_mode")
        or r.get("runtime_policy_mode")
        or r.get("c4_runtime_mode")
        or ""
    )


def _failure_mode(rec: dict[str, Any]) -> str:

    """Coarse failure taxonomy for paired mutation regressions."""
    delta = float(rec.get("delta") or 0.0)
    if delta <= 0:
        baseline_steps = int(rec.get("baseline_num_actions") or 0)
        mutation_steps = int(rec.get("mutation_num_actions") or 0)
        if mutation_steps > baseline_steps + 2:
            return "near_miss"
        return "agent_compatible"

    mode = _rule_mode(rec)
    if _oracle_rule_violation(rec):
        if mode in {"silent", "C4b", "silent_business_rule_drift", "O0_silent"}:
            return "silent_failure"
        if rec.get("generic_error_visible"):
            return "generic_error_unrecovered"
        if rec.get("structured_policy_error_visible"):
            return "structured_recovery_failure"
        if rec.get("migration_note_visible"):
            return "migration_note_ignored"
        return "recovery_failure"
    if _visible_policy_error(rec):
        return "loud_failure"

    return "silent_failure"


def _summarize(records: list[dict[str, Any]], label: str) -> None:

    if not records:
        print(f"\n[{label}] no paired records")
        return
    deltas = [r["delta"] for r in records]
    base = [r["baseline_reward"] for r in records]
    mut = [r["mutation_reward"] for r in records]
    print(f"\n[{label}] paired_records={len(records)}")
    print(f"  baseline_success={sum(base)/len(base):.3f}")
    print(f"  mutation_success={sum(mut)/len(mut):.3f}")
    print(f"  mean_drop={sum(deltas)/len(deltas):.3f}")
    print(f"  drops>0={sum(1 for d in deltas if d > 0)}/{len(deltas)}")

    by_task: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in records:
        by_task[int(r["task_index"])].append(r)
    print("  per_task:")
    for t in sorted(by_task):
        rs = by_task[t]
        b = [x["baseline_reward"] for x in rs]
        m = [x["mutation_reward"] for x in rs]
        d = [x["delta"] for x in rs]
        print(
            f"    task={t:02d} n={len(rs)} "
            f"base={sum(b)/len(b):.3f} mut={sum(m)/len(m):.3f} "
            f"drop={sum(d)/len(d):.3f} "
            f"mut_tools={sorted(set(str(x.get('mutation_tool')) for x in rs))}"
        )

    # Policy/oracle stats
    applied = sum(1 for r in records if r.get("mutation_applied"))
    oracle = sum(1 for r in records if _oracle_rule_violation(r))
    visible = sum(1 for r in records if _visible_policy_error(r))
    generic = sum(1 for r in records if r.get("generic_error_visible"))
    structured = sum(1 for r in records if r.get("structured_policy_error_visible"))
    migration = sum(1 for r in records if r.get("migration_note_visible"))
    print(f"  mutation_applied={applied}/{len(records)}")
    print(f"  oracle_rule_violation={oracle}/{len(records)}")
    print(f"  visible_policy_error={visible}/{len(records)}")
    print(f"  generic_error_visible={generic}/{len(records)}")
    print(f"  structured_policy_error_visible={structured}/{len(records)}")
    print(f"  migration_note_visible={migration}/{len(records)}")
    modes = collections.Counter(str(r.get("failure_mode")) for r in records)

    print("  failure_modes=" + ", ".join(f"{k}:{v}" for k, v in sorted(modes.items())))





def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", required=True, help="JSONL containing baseline records")
    p.add_argument(
        "--mutations",
        nargs="+",
        required=True,
        help="label=path pairs, e.g. used=file.jsonl unused=file.jsonl",
    )
    p.add_argument("--applied-only", action="store_true")
    p.add_argument("--successful-baseline-only", action="store_true")
    p.add_argument("--out", default=None, help="optional detailed paired JSONL output")
    args = p.parse_args()

    baseline_rows = _load_latest(Path(args.baseline))
    baseline: dict[tuple[Any, ...], dict[str, Any]] = {}
    for r in baseline_rows:
        if r.get("status") != "ok":
            continue
        if r.get("mutation_type") is not None:
            continue
        baseline[_base_key(r)] = r

    print(f"baseline_file={args.baseline}")
    print(f"baseline_cells={len(baseline)}")

    all_detail: list[dict[str, Any]] = []
    for spec in args.mutations:
        if "=" not in spec:
            raise ValueError(f"mutation spec must be label=path: {spec}")
        label, path_s = spec.split("=", 1)
        rows = _load_latest(Path(path_s))
        paired: list[dict[str, Any]] = []
        missing_base = 0
        skipped_not_ok = 0
        skipped_not_applied = 0
        skipped_base_fail = 0

        for r in rows:
            if r.get("status") != "ok":
                skipped_not_ok += 1
                continue
            if args.applied_only and not r.get("mutation_applied"):
                skipped_not_applied += 1
                continue
            b = baseline.get(_base_key(r))
            if b is None:
                missing_base += 1
                continue
            if args.successful_baseline_only and _reward(b) <= 0:
                skipped_base_fail += 1
                continue

            rec = {
                "label": label,
                "task_index": r.get("task_index"),
                "model": r.get("model"),
                "seed": r.get("seed"),
                "mutation_type": r.get("mutation_type"),
                "target_policy": r.get("target_policy", "random"),
                "c4_runtime_mode": r.get("c4_runtime_mode"),
                "observability_level": r.get("observability_level"),
                "baseline_reward": _reward(b),
                "mutation_reward": _reward(r),
                "delta": _reward(b) - _reward(r),
                "baseline_num_actions": _num_actions(b),
                "mutation_num_actions": _num_actions(r),
                "mutation_applied": r.get("mutation_applied"),
                "mutation_tool": r.get("mutation_tool"),
                "mutation_note": r.get("mutation_note"),
                "oracle_rule_violation": r.get("oracle_rule_violation", r.get("runtime_policy_violation")),
                "visible_policy_error": r.get("visible_policy_error"),
                "generic_error_visible": r.get("generic_error_visible"),
                "structured_policy_error_visible": r.get("structured_policy_error_visible"),
                "migration_note_visible": r.get("migration_note_visible"),
                "hidden_business_rule_violation": r.get("hidden_business_rule_violation"),
                "recovery_attempted": r.get("recovery_attempted"),
                "recovery_success": r.get("recovery_success"),
                "final_reward": r.get("final_reward", r.get("reward")),
                "oracle_rule_action": r.get("oracle_rule_action", r.get("runtime_policy_action")),
                "oracle_rule_error": r.get("oracle_rule_error", r.get("runtime_policy_error")),
                "oracle_rule_mode": r.get("oracle_rule_mode", r.get("runtime_policy_mode")),
                "oracle_force_zero": r.get("oracle_force_zero", r.get("runtime_policy_force_zero")),
                "runtime_policy_violation": r.get("runtime_policy_violation"),
                "runtime_policy_action": r.get("runtime_policy_action"),
                "runtime_policy_error": r.get("runtime_policy_error"),
                "runtime_policy_mode": r.get("runtime_policy_mode"),
            }

            rec["failure_mode"] = _failure_mode(rec)

            paired.append(rec)
            all_detail.append(rec)

        print(
            f"\nlabel={label} file={path_s} raw_latest={len(rows)} "
            f"paired={len(paired)} missing_base={missing_base} "
            f"skip_not_ok={skipped_not_ok} skip_not_applied={skipped_not_applied} "
            f"skip_base_fail={skipped_base_fail}"
        )
        _summarize(paired, label)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for r in all_detail:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\ndetail_written={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
