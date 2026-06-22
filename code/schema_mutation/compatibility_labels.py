"""Attach traditional-vs-agent compatibility labels to mutation results.

Goal: turn raw mutation trajectories into an ICSE-style 2×2 table:

                      Agent compatible    Agent breaking
Traditional compat          ...             HERO REGION
Traditional breaking        ...             ...

This is deliberately simple for the pilot. It uses the v2 ATTRIBUTE_MATRIX from
mutator.py as the traditional/static side, and paired baseline-vs-mutation
results as the agent side.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

from code.schema_mutation.mutator import ATTRIBUTE_MATRIX

LEGACY_TO_V2 = {
    None: "baseline",
    "M01_rename": "A1_identifier_rename",
    "M02_type_change": "B1_type_change",
    "M03_requiredness": "B2_requiredness_change",
    "M04_default_semantic_drift": "C2_currency_locale_drift",
    "M05_unit_change": "C1_unit_scale_drift",
    "M06_enum_rename": "B3_enum_change",
    "M07_description_paraphrase": "A3_paraphrase_meaning_preserving",
    "M08_error_format": "D1_error_format_change",
    "M09_permission_change": "D2_permission_change",
    "M10_pagination_change": "D3_pagination_change",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _mutation_v2(mutation_type: str | None) -> str:
    if mutation_type in ATTRIBUTE_MATRIX:
        return str(mutation_type)
    return LEGACY_TO_V2.get(mutation_type, str(mutation_type))


def _trad_bucket(attrs: dict[str, str]) -> str:
    # For pilot: Y => compatible; N => breaking; P/? => ambiguous.
    tc = attrs.get("traditional_compatible", "?")
    if tc == "Y":
        return "traditional_compatible"
    if tc == "N":
        return "traditional_breaking"
    return "traditional_ambiguous"


def _agent_bucket(delta: float) -> str:
    return "agent_breaking" if delta > 0 else "agent_compatible"


def _hero_rate(rows: list[dict[str, Any]], trad_labels: set[str], exclude: set[str] | None = None) -> tuple[int, int, float]:
    exclude = exclude or set()
    scoped = [
        r for r in rows
        if r.get("attrs", {}).get("traditional_compatible") in trad_labels
        and r.get("mutation_type_v2") not in exclude
    ]
    breaks = [r for r in scoped if r.get("agent_bucket") == "agent_breaking"]
    rate = len(breaks) / len(scoped) if scoped else 0.0
    return len(breaks), len(scoped), rate


def main() -> int:

    p = argparse.ArgumentParser()
    p.add_argument("paired_jsonl", help="output of paired_analyzer.py")
    p.add_argument("--out", default=None, help="write labeled paired JSONL")
    args = p.parse_args()

    rows = _load_jsonl(Path(args.paired_jsonl))
    labeled = []
    table: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    by_mut: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)

    for r in rows:
        mt = _mutation_v2(r.get("mutation_type"))
        attrs = ATTRIBUTE_MATRIX.get(mt, {})
        trad = _trad_bucket(attrs) if attrs else "unknown_traditional"
        agent = _agent_bucket(float(r.get("delta") or 0.0))
        rec = dict(r)
        rec.update(
            {
                "mutation_type_v2": mt,
                "attrs": attrs,
                "traditional_bucket": trad,
                "agent_bucket": agent,
                "hero_region": trad == "traditional_compatible" and agent == "agent_breaking",
            }
        )
        labeled.append(rec)
        table[(trad, agent)].append(rec)
        by_mut[mt].append(rec)

    print(f"input={args.paired_jsonl}")
    print(f"records={len(labeled)}")
    print("\n--- 2x2 / 3x2 table ---")
    row_names = ["traditional_compatible", "traditional_breaking", "traditional_ambiguous", "unknown_traditional"]
    col_names = ["agent_compatible", "agent_breaking"]
    for rn in row_names:
        counts = [len(table.get((rn, cn), [])) for cn in col_names]
        if sum(counts) == 0:
            continue
        print(f"{rn:<26} compatible={counts[0]:<4} breaking={counts[1]:<4}")

    hero = table.get(("traditional_compatible", "agent_breaking"), [])
    tc_total = len(table.get(("traditional_compatible", "agent_compatible"), [])) + len(hero)
    strict_breaks, strict_total, strict_rate = _hero_rate(labeled, {"Y"})
    relaxed_breaks, relaxed_total, relaxed_rate = _hero_rate(labeled, {"Y", "P"})
    no_a2_breaks, no_a2_total, no_a2_rate = _hero_rate(labeled, {"Y"}, {"A2_format_change"})
    print("\n--- hero region ---")
    print(f"traditional-compatible & agent-breaking: {len(hero)}")
    if tc_total:
        print(f"hero_rate_within_traditional_compatible={len(hero)/tc_total:.3f}")
    print(f"strict_Y_only={strict_breaks}/{strict_total} rate={strict_rate:.3f}")
    print(f"relaxed_Y_plus_P={relaxed_breaks}/{relaxed_total} rate={relaxed_rate:.3f}")
    print(f"strict_Y_excluding_A2={no_a2_breaks}/{no_a2_total} rate={no_a2_rate:.3f}")
    print("examples:")

    for r in hero[:10]:
        print(
            f"  label={r.get('label')} task={r.get('task_index')} seed={r.get('seed')} "
            f"mut={r.get('mutation_type_v2')} tool={r.get('mutation_tool')} "
            f"delta={r.get('delta')} oracle_violation={r.get('oracle_rule_violation', r.get('runtime_policy_violation'))} "
            f"visible_error={r.get('visible_policy_error')}"

        )

    print("\n--- by mutation ---")
    for mt, rs in sorted(by_mut.items()):
        deltas = [float(r.get("delta") or 0) for r in rs]
        breaks = sum(1 for d in deltas if d > 0)
        attrs = ATTRIBUTE_MATRIX.get(mt, {})
        print(
            f"{mt:<34} n={len(rs):<3} break={breaks:<3} "
            f"mean_drop={sum(deltas)/len(deltas):.3f} "
            f"trad={attrs.get('traditional_compatible', '?')} "
            f"schema_visible={attrs.get('schema_visible', '?')} "
            f"semantics={attrs.get('semantics_changing', '?')}"
        )

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            for r in labeled:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nlabeled_written={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
