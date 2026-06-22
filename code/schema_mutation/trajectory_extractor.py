"""Extract tool exposure from baseline-successful trajectories.

This is the first step from a random mutation benchmark to an exposure-aware
compatibility testing protocol.

Input: batch_runner JSONL, usually baseline selection output.
Output: JSON map:
    {
      "0": {
        "records": 3,
        "success_records": 3,
        "used_tools": ["get_order_details", ...],
        "used_params_by_tool": {"get_order_details": ["order_id"], ...},
        "tool_counts": {"get_order_details": 3, ...},
        "param_counts_by_tool": {"get_order_details": {"order_id": 3}, ...}
      },
      ...
    }

Example:
    python -m code.schema_mutation.trajectory_extractor \
      runs/schema_mutation/day6_baseline_selection_deepseek.jsonl \
      --out runs/schema_mutation/exposure_map_deepseek_baseline_good.json
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

RESPOND_TOOL = "respond"


def record_exposure_level(record: dict[str, Any]) -> str:
    """Infer a coarse exposure level for gate features.

    This helper only uses baseline/candidate routing metadata and action names.
    It does not use final success labels.
    """
    policy = str(record.get("target_policy") or "random")
    if policy in {"unused_tool", "unused_intent_aligned"}:
        return "unexposed"
    if policy in {"intent_aligned", "random_intent_aligned"}:
        return "intent_aligned"
    if policy == "used_tool":
        return "used_tool"
    target = record.get("target_tool") or record.get("mutation_tool")
    if target:
        actions = _extract_actions(record)
        if any(a.get("name") == target for a in actions):
            return "executed_target_tool"
        return "candidate_tool"
    return "unknown"


def _cell_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("task_index"),
        record.get("model"),
        record.get("mutation_type"),
        record.get("seed"),
        record.get("env_user_model"),
        record.get("env_user_provider"),
        record.get("temperature"),
    )


def _load_rows(path: Path, latest: bool) -> list[dict[str, Any]]:
    rows = [
        json.loads(l)
        for l in path.read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    if not latest:
        return rows
    dedup: dict[tuple[Any, ...], dict[str, Any]] = {}
    for r in rows:
        dedup[_cell_key(r)] = r
    return list(dedup.values())


def _extract_actions(record: dict[str, Any]) -> list[dict[str, Any]]:
    raw = record.get("raw") or {}
    actions = raw.get("taken_actions") or []
    if isinstance(actions, list):
        return [a for a in actions if isinstance(a, dict)]
    return []


def build_exposure_map(
    rows: list[dict[str, Any]],
    only_success: bool = True,
    include_respond: bool = False,
) -> dict[str, Any]:
    per_task: dict[str, dict[str, Any]] = {}

    for r in rows:
        if r.get("status") != "ok":
            continue
        if r.get("mutation_type") is not None:
            continue
        if only_success and float(r.get("reward") or 0) <= 0:
            continue

        task_id = str(r.get("task_index"))
        d = per_task.setdefault(
            task_id,
            {
                "records": 0,
                "success_records": 0,
                "tool_counts": collections.Counter(),
                "param_counts_by_tool": collections.defaultdict(collections.Counter),
                "action_lengths": [],
                "models": collections.Counter(),
            },
        )
        d["records"] += 1
        d["success_records"] += 1 if float(r.get("reward") or 0) > 0 else 0
        d["models"][r.get("model", "<unknown>")] += 1

        actions = _extract_actions(r)
        d["action_lengths"].append(len(actions))
        for a in actions:
            name = a.get("name")
            if not name:
                continue
            if name == RESPOND_TOOL and not include_respond:
                continue
            d["tool_counts"][name] += 1
            kwargs = a.get("kwargs") or {}
            if isinstance(kwargs, dict):
                for k in kwargs:
                    d["param_counts_by_tool"][name][k] += 1

    # Convert counters/defaultdicts to plain JSON-friendly structures
    out: dict[str, Any] = {}
    for task_id, d in sorted(per_task.items(), key=lambda kv: int(kv[0])):
        tool_counts = dict(d["tool_counts"])
        param_counts = {
            tool: dict(counter)
            for tool, counter in d["param_counts_by_tool"].items()
        }
        out[task_id] = {
            "records": d["records"],
            "success_records": d["success_records"],
            "used_tools": sorted(tool_counts, key=lambda x: (-tool_counts[x], x)),
            "used_params_by_tool": {
                tool: sorted(params, key=lambda p: (-param_counts[tool][p], p))
                for tool, params in param_counts.items()
            },
            "tool_counts": tool_counts,
            "param_counts_by_tool": param_counts,
            "mean_action_length": (
                sum(d["action_lengths"]) / len(d["action_lengths"])
                if d["action_lengths"] else 0.0
            ),
            "models": dict(d["models"]),
        }
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jsonl")
    p.add_argument("--out", default=None)
    p.add_argument("--latest", action="store_true", help="deduplicate append-resume JSONL by cell")
    p.add_argument("--include-failed", action="store_true", help="include baseline failures too")
    p.add_argument("--include-respond", action="store_true", help="include respond pseudo-tool")
    args = p.parse_args()

    in_path = Path(args.jsonl)
    rows = _load_rows(in_path, latest=args.latest)
    exposure = build_exposure_map(
        rows,
        only_success=not args.include_failed,
        include_respond=args.include_respond,
    )

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = in_path.with_suffix(".exposure.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(exposure, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"input_rows={len(rows)} tasks_with_exposure={len(exposure)} out={out_path}")
    for task_id, d in exposure.items():
        tools = ",".join(d["used_tools"][:8])
        print(
            f"task={task_id:<3} records={d['records']} success={d['success_records']} "
            f"tools={tools}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
