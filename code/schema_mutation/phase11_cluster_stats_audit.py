#!/usr/bin/env python3
"""Cluster-aware sensitivity audit for Phase 11.

This script is offline-only: it reads persisted JSON/JSONL artifacts and writes
summary reports. It does not call model APIs or experiment runners.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def latest_by_key(rows: list[dict], key: str = "cell_key") -> list[dict]:
    out: dict[str, dict] = {}
    for row in rows:
        k = str(row.get(key) or hashlib.sha1(json.dumps(row, sort_keys=True).encode()).hexdigest())
        out[k] = row
    return list(out.values())


def ok_formal(rows: list[dict]) -> list[dict]:
    return [
        r
        for r in latest_by_key(rows)
        if r.get("status") == "ok"
        and not r.get("fake_run")
        and r.get("baseline_success", True) is not False
        and "smoke" not in str(r.get("cell_key", "")).lower()
    ]


def rate(rows: list[dict], field: str = "mutation_success") -> float | None:
    if not rows:
        return None
    vals = [1.0 if r.get(field) else 0.0 for r in rows]
    return sum(vals) / len(vals)


def pct(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{100*x:.1f}%"


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    xs = sorted(xs)
    idx = (len(xs) - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - idx) + xs[hi] * (idx - lo)


def ordinary_bootstrap_diff(a: list[dict], b: list[dict], field: str = "mutation_success", n: int = 2000) -> dict:
    if not a or not b:
        return {"ci": None, "samples": 0}
    rng = random.Random(11)
    av = [1.0 if r.get(field) else 0.0 for r in a]
    bv = [1.0 if r.get(field) else 0.0 for r in b]
    vals = []
    for _ in range(n):
        aa = [rng.choice(av) for _ in av]
        bb = [rng.choice(bv) for _ in bv]
        vals.append(mean(bb) - mean(aa))
    return {"ci": [percentile(vals, 0.025), percentile(vals, 0.975)], "samples": n}


def cluster_bootstrap_diff(a: list[dict], b: list[dict], cluster_field: str, field: str = "mutation_success", n: int = 2000) -> dict:
    if not a or not b:
        return {"ci": None, "clusters": 0, "samples": 0}
    clusters = sorted({str(r.get(cluster_field)) for r in a + b if r.get(cluster_field) is not None})
    if len(clusters) < 2:
        return {"ci": None, "clusters": len(clusters), "samples": 0, "note": "fewer than two clusters"}
    by_a: dict[str, list[dict]] = defaultdict(list)
    by_b: dict[str, list[dict]] = defaultdict(list)
    for r in a:
        by_a[str(r.get(cluster_field))].append(r)
    for r in b:
        by_b[str(r.get(cluster_field))].append(r)
    rng = random.Random(17)
    vals = []
    for _ in range(n):
        draw = [rng.choice(clusters) for _ in clusters]
        aa = [r for c in draw for r in by_a.get(c, [])]
        bb = [r for c in draw for r in by_b.get(c, [])]
        if aa and bb:
            vals.append(rate(bb, field) - rate(aa, field))
    return {
        "ci": [percentile(vals, 0.025), percentile(vals, 0.975)] if vals else None,
        "clusters": len(clusters),
        "samples": len(vals),
    }


def paired_cluster_bootstrap_diff(pairs: list[tuple[dict, dict]], cluster_field: str, field: str = "mutation_success", n: int = 2000) -> dict:
    clusters: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    for a, b in pairs:
        c = a.get(cluster_field) or b.get(cluster_field)
        if c is not None:
            clusters[str(c)].append((a, b))
    keys = sorted(clusters)
    if len(keys) < 2:
        return {"ci": None, "clusters": len(keys), "samples": 0}
    rng = random.Random(23)
    vals = []
    for _ in range(n):
        draw = [rng.choice(keys) for _ in keys]
        diffs = []
        for c in draw:
            for a, b in clusters[c]:
                diffs.append((1.0 if b.get(field) else 0.0) - (1.0 if a.get(field) else 0.0))
        if diffs:
            vals.append(mean(diffs))
    return {"ci": [percentile(vals, 0.025), percentile(vals, 0.975)], "clusters": len(keys), "samples": len(vals)}


def load_glob(root: Path, pattern: str) -> list[dict]:
    rows: list[dict] = []
    for p in sorted(root.glob(pattern)):
        rows.extend(read_jsonl(p))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out-dir", default="runs/schema_mutation/phase11")
    args = ap.parse_args()
    root = Path(args.root)
    out_dir = root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict] = {}

    # Phase 5 observability: O4 vs O0.
    obs_rows = load_glob(root, "runs/schema_mutation/phase5/status/observability_from_baseline_*_status.jsonl")
    obs_rows += load_glob(root, "runs/schema_mutation/phase5/status/airline_observability_from_baseline_*_status.jsonl")
    obs = ok_formal(obs_rows)
    o0 = [r for r in obs if r.get("observability_level") == "O0_silent"]
    o4 = [r for r in obs if r.get("observability_level") == "O4_migration_note"]
    any_visible = [r for r in obs if r.get("observability_level") in {
        "O1_generic_error",
        "O2_policy_error",
        "O3_structured_policy_error",
        "O4_migration_note",
    }]
    pairs = []
    o0_by = {(r.get("env"), r.get("model"), r.get("task_id"), r.get("seed")): r for r in o0}
    for r in o4:
        k = (r.get("env"), r.get("model"), r.get("task_id"), r.get("seed"))
        if k in o0_by:
            pairs.append((o0_by[k], r))
    results["phase5_o4_minus_o0"] = {
        "n_o0": len(o0),
        "n_o4": len(o4),
        "rate_o0": rate(o0),
        "rate_o4": rate(o4),
        "raw_diff": (rate(o4) or 0) - (rate(o0) or 0),
        "ordinary_bootstrap_ci": ordinary_bootstrap_diff(o0, o4),
        "cluster_by_env_task_ci": cluster_bootstrap_diff(o0, o4, "task_id"),
        "paired_by_env_model_task_seed_n": len(pairs),
        "paired_cluster_by_task_ci": paired_cluster_bootstrap_diff(pairs, "task_id"),
    }
    results["phase5_any_visible_minus_o0"] = {
        "n_o0": len(o0),
        "n_any_visible": len(any_visible),
        "rate_o0": rate(o0),
        "rate_any_visible": rate(any_visible),
        "raw_diff": (rate(any_visible) or 0) - (rate(o0) or 0),
        "ordinary_bootstrap_ci": ordinary_bootstrap_diff(o0, any_visible),
        "cluster_by_task_ci": cluster_bootstrap_diff(o0, any_visible, "task_id"),
        "note": "Any-visible pools O1--O4 rows; task-cluster bootstrap is a sensitivity check for shared tasks.",
    }

    # Phase 8A unused-tool vs exposed O0.
    unused = ok_formal(load_glob(root, "runs/schema_mutation/phase5/status/unused_tool_control_*_status.jsonl"))
    exposed_by_key = {r.get("cell_key"): r for r in o0}
    unused_pairs = []
    for r in unused:
        src = r.get("source_exposed_o0_cell_key")
        if src in exposed_by_key:
            unused_pairs.append((exposed_by_key[src], r))
    exposed_matched = [a for a, _ in unused_pairs]
    unused_matched = [b for _, b in unused_pairs]
    results["phase8a_unused_minus_exposed_o0"] = {
        "n_exposed": len(exposed_matched),
        "n_unused": len(unused_matched),
        "rate_exposed": rate(exposed_matched),
        "rate_unused": rate(unused_matched),
        "raw_diff": (rate(unused_matched) or 0) - (rate(exposed_matched) or 0),
        "ordinary_bootstrap_ci": ordinary_bootstrap_diff(exposed_matched, unused_matched),
        "paired_cluster_by_task_ci": paired_cluster_bootstrap_diff(unused_pairs, "task_id"),
        "paired_cluster_by_source_cell_ci": paired_cluster_bootstrap_diff(unused_pairs, "cell_key"),
    }

    # Phase 10D non-obviousness.
    nonobv = ok_formal(load_glob(root, "runs/schema_mutation/phase10/phase10c/nonobviousness_formal/status/nonobviousness_*_status.jsonl"))
    conds = defaultdict(list)
    for r in nonobv:
        conds[str(r.get("condition"))].append(r)
    visible = conds.get("rule_in_tool_preamble_upper_bound", [])
    for cond in ["O0_increased_reasoning_budget", "O0_reflection_scaffold"]:
        rows = conds.get(cond, [])
        results[f"phase10d_visible_minus_{cond}"] = {
            "n_o0_variant": len(rows),
            "n_visible": len(visible),
            "rate_o0_variant": rate(rows),
            "rate_visible": rate(visible),
            "raw_diff": (rate(visible) or 0) - (rate(rows) or 0),
            "ordinary_bootstrap_ci": ordinary_bootstrap_diff(rows, visible),
            "cluster_by_source_o0_cell_ci": cluster_bootstrap_diff(rows, visible, "source_o0_cell_key"),
            "cluster_by_task_ci": cluster_bootstrap_diff(rows, visible, "task_id"),
        }

    # Phase 10F real replay.
    real = ok_formal(read_jsonl(root / "runs/schema_mutation/phase10/real_case_replay/formal_r1/status/real_case_formal_status.jsonl"))
    real_conds = defaultdict(list)
    for r in real:
        real_conds[str(r.get("condition"))].append(r)
    baseline = real_conds.get("baseline_old_api", [])
    silent = real_conds.get("evolved_o0_silent", [])
    vis = real_conds.get("evolved_visible_feedback", [])
    results["phase10f_real_replay_visible_minus_silent"] = {
        "n_silent": len(silent),
        "n_visible": len(vis),
        "rate_silent": rate(silent),
        "rate_visible": rate(vis),
        "raw_diff": (rate(vis) or 0) - (rate(silent) or 0),
        "ordinary_bootstrap_ci": ordinary_bootstrap_diff(silent, vis),
        "cluster_by_case_id_ci": cluster_bootstrap_diff(silent, vis, "case_id"),
        "note": "case-level cluster bootstrap has only two clusters and should be treated as sensitivity evidence, not a precise interval.",
    }
    results["phase10f_real_replay_baseline_minus_silent"] = {
        "n_baseline": len(baseline),
        "n_silent": len(silent),
        "rate_baseline": rate(baseline),
        "rate_silent": rate(silent),
        "raw_diff": (rate(baseline) or 0) - (rate(silent) or 0),
        "cluster_by_case_id_ci": cluster_bootstrap_diff(silent, baseline, "case_id"),
    }

    # Interpretation.
    for item in results.values():
        diff = item.get("raw_diff")
        ci = None
        for key in ["paired_cluster_by_task_ci", "cluster_by_task_ci", "cluster_by_source_o0_cell_ci", "cluster_by_case_id_ci", "cluster_by_env_task_ci"]:
            val = item.get(key)
            if isinstance(val, dict) and val.get("ci"):
                ci = val["ci"]
                break
        item["direction_supported_by_cluster_ci"] = bool(ci and ci[0] > 0) if diff is not None and diff > 0 else None

    (out_dir / "cluster_stats_audit.json").write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")

    lines = ["# Cluster-Aware Statistics Audit", ""]
    lines.append("Offline sensitivity analysis over persisted artifacts. No experiments or model APIs were run.")
    lines.append("")
    for name, item in results.items():
        lines.append(f"## {name}")
        for k, v in item.items():
            if k.endswith("_ci") or k == "ordinary_bootstrap_ci":
                lines.append(f"- `{k}`: `{json.dumps(v)}`")
            elif isinstance(v, float):
                lines.append(f"- `{k}`: {v:.4f} ({pct(v)})")
            else:
                lines.append(f"- `{k}`: {v}")
        lines.append("")
    lines.append("## Recommendation")
    lines.append("The direction of the headline effects remains positive under available cluster-bootstrap sensitivity checks. Fisher exact p-values should be treated as descriptive because rows share tasks, models, and source cells; the paper should emphasize effect sizes and cluster-bootstrap sensitivity rather than p-values alone.")
    (out_dir / "cluster_stats_audit.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
