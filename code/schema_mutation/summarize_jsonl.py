"""Summarize schema-mutation batch JSONL outputs.

Use --latest to deduplicate append-resume files by (task, model, mutation,
seed, user-model, provider, temperature), keeping the latest record per cell.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any


def _cell_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("task_index"),
        record.get("model"),
        record.get("mutation_type"),
        record.get("seed"),
        record.get("env_user_model"),
        record.get("env_user_provider"),
        record.get("temperature"),
        record.get("target_policy", "random"),
        record.get("observability_level"),
        record.get("c4_runtime_mode"),
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--latest", action="store_true", help="deduplicate by cell, keep latest record")
    p.add_argument("--no-rows", action="store_true", help="do not print every row")
    args = p.parse_args()
    path = Path(args.path)
    raw_rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = raw_rows
    if args.latest:
        latest: dict[tuple[Any, ...], dict[str, Any]] = {}
        for r in raw_rows:
            latest[_cell_key(r)] = r
        rows = list(latest.values())

    print(f"file: {path}")
    print(f"raw_rows: {len(raw_rows)}")
    if args.latest:
        print(f"latest_cells: {len(rows)}")
    print(f"status: {dict(collections.Counter(r['status'] for r in rows))}")

    if not args.no_rows:
        print("\n--- rows ---")
        for r in rows:
            model = r["model"].split("/")[-1]
            mut = r.get("mutation_type") or "baseline"
            obs = r.get("observability_level") or "-"
            print(
                f"task={r['task_index']:<2} model={model:<32} mut={mut:<28} "
                f"obs={obs:<28} "
                f"status={r['status']:<5} reward={r.get('reward')} "
                f"applied={r.get('mutation_applied')} actions={r.get('num_actions')} "
                f"err={str(r.get('error', ''))[:70]}"
            )

    print("\n--- by mutation ---")
    by = collections.defaultdict(list)
    for r in rows:
        if r["status"] == "ok":
            by[r.get("mutation_type") or "baseline"].append(float(r.get("reward") or 0))
    for k, v in by.items():
        print(f"{k:<28} n={len(v):<3} success={sum(v)/len(v):.3f} rewards={v}")

    print("\n--- by observability ---")
    by_obs = collections.defaultdict(list)
    for r in rows:
        if r["status"] == "ok":
            key = r.get("observability_level") or r.get("c4_runtime_mode") or "baseline"
            by_obs[key].append(float(r.get("reward") or 0))
    for k, v in sorted(by_obs.items()):
        print(f"{k:<28} n={len(v):<3} success={sum(v)/len(v):.3f} rewards={v}")

    print("\n--- by model × mutation ---")
    by2 = collections.defaultdict(list)
    for r in rows:
        if r["status"] == "ok":
            obs = r.get("observability_level") or r.get("c4_runtime_mode") or "-"
            by2[(r["model"].split("/")[-1], r.get("mutation_type") or "baseline", obs)].append(float(r.get("reward") or 0))
    for (model, mut, obs), v in sorted(by2.items()):
        print(f"{model:<32} {mut:<28} {obs:<28} n={len(v):<3} success={sum(v)/len(v):.3f} rewards={v}")

    errors = [r for r in rows if r["status"] != "ok"]
    if errors:
        print("\n--- errors ---")
        for r in errors[:50]:
            print(f"{r['model']} {r.get('mutation_type')} {r.get('error_type')}: {r.get('error')}")
        if len(errors) > 50:
            print(f"... {len(errors) - 50} more errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
