"""Extract rows for one mutation from a batch JSONL file.

Useful for feeding paired_analyzer.py, whose mutation inputs are label=path.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("--mutation", required=True, help="mutation name; use baseline for None")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    want = None if args.mutation.lower() in {"baseline", "none", "null"} else args.mutation
    n = 0
    with src.open("r", encoding="utf-8") as fin, out.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("mutation_type") == want:
                fout.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
    print(f"wrote {n} rows: mutation={args.mutation} out={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
