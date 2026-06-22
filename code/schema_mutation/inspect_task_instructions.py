"""Print task instructions from a schema-mutation JSONL file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jsonl")
    p.add_argument("--tasks", default=None)
    args = p.parse_args()
    wanted = None
    if args.tasks:
        wanted = {int(x.strip()) for x in args.tasks.split(",") if x.strip()}
    rows = [json.loads(l) for l in Path(args.jsonl).read_text(encoding="utf-8").splitlines() if l.strip()]
    seen = set()
    for r in rows:
        t = int(r.get("task_index"))
        if wanted is not None and t not in wanted:
            continue
        if t in seen or r.get("status") != "ok" or float(r.get("reward") or 0) <= 0:
            continue
        seen.add(t)
        instr = (((r.get("raw") or {}).get("task") or {}).get("instruction") or "").replace("\n", " ")
        print(f"TASK {t}: {instr[:1000]}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
