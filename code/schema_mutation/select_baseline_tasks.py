"""Select baseline-solvable tasks from a batch JSONL file."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--threshold", type=float, default=2/3)
    args = p.parse_args()
    path = Path(args.path)
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    by = collections.defaultdict(list)
    actions = collections.defaultdict(list)
    errors = []
    for r in rows:
        if r.get("status") != "ok":
            errors.append(r)
            continue
        by[int(r["task_index"])].append(float(r.get("reward") or 0))
        actions[int(r["task_index"])].append(float(r.get("num_actions") or 0))

    print(f"file: {path}")
    print(f"rows={len(rows)} ok={len(rows)-len(errors)} errors={len(errors)} threshold={args.threshold:.3f}")
    print("\n--- per task ---")
    good, maybe, bad = [], [], []
    for t in sorted(by):
        v = by[t]
        rate = sum(v) / len(v)
        mean_actions = sum(actions[t]) / len(actions[t])
        bucket = good if rate >= args.threshold else maybe if rate >= 1/3 else bad
        bucket.append(t)
        print(f"task={t:02d} success={rate:.3f} rewards={v} mean_actions={mean_actions:.1f}")

    total_success = sum(sum(v) for v in by.values())
    total_n = sum(len(v) for v in by.values())
    print("\n--- selection ---")
    print(f"GOOD >= {args.threshold:.3f}: {good}")
    print(f"MAYBE >= 0.333: {maybe}")
    print(f"BAD < 0.333: {bad}")
    print(f"overall_success={total_success/total_n:.3f} ({int(total_success)}/{total_n})")
    print("\nCSV_GOOD=" + ",".join(map(str, good)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
