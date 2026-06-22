from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jsonl")
    args = p.parse_args()
    rows = [json.loads(l) for l in Path(args.jsonl).read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        mut = r.get("mutation_meta") or {}
        print("TASK", r.get("task_index"), "reward", r.get("reward"), "tool", r.get("mutation_tool"), "intent", mut.get("task_intent"), "runtime", mut.get("runtime_semantics_changed"))
        print("actions:", [a.get("name") for a in (r.get("raw") or {}).get("taken_actions", [])])
        # print policy errors if present in raw action list? observations are not stored, so just actions.
        print("note:", r.get("mutation_note"))
        print("---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
