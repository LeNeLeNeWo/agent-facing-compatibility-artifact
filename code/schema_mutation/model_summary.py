"""Summarize paired mutation results by model and label."""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jsonl", nargs="+")
    args = p.parse_args()

    rows: list[dict[str, Any]] = []
    for path_s in args.jsonl:
        rows.extend(_load_jsonl(Path(path_s)))

    groups: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for r in rows:
        groups[(str(r.get("model")), str(r.get("label")))].append(r)

    print("model\tlabel\tn\tmut_success\tmean_drop\tdrops\toracle_violation\tvisible_error\tfailure_modes")

    for (model, label), rs in sorted(groups.items()):
        rewards = [float(r.get("mutation_reward") or 0.0) for r in rs]
        deltas = [float(r.get("delta") or 0.0) for r in rs]
        drops = sum(1 for d in deltas if d > 0)
        runtime = sum(1 for r in rs if r.get("runtime_policy_violation"))
        modes = collections.Counter(str(r.get("failure_mode")) for r in rs)
        mode_s = ",".join(f"{k}:{v}" for k, v in sorted(modes.items()))
        print(
            f"{model}\t{label}\t{len(rs)}\t{_mean(rewards):.3f}\t{_mean(deltas):.3f}\t"
            f"{drops}/{len(rs)}\t{runtime}/{len(rs)}\t{mode_s}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
