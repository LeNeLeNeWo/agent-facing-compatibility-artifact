"""Summarize Phase 5 status JSONL files into audit and paper artifacts."""

from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from code.schema_mutation.c4_observability_modes import OBSERVABILITY_LEVELS, observability_order  # noqa: E402

RUNS = _REPO_ROOT / "runs" / "schema_mutation" / "phase5"
PAPER = _REPO_ROOT / "IEEE_Conference_Template"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        print(f"[warn] missing input: {path}")
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                row.setdefault("_source_artifact", str(path))
                rows.append(row)
            except json.JSONDecodeError as exc:
                print(f"[warn] {path}:{line_no}: {exc}")
    return rows


def _cell_key(row: dict[str, Any]) -> str:
    return str(row.get("cell_key") or "")


def _latest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        latest[_cell_key(row)] = row
    return list(latest.values())


def _is_smoke(row: dict[str, Any]) -> bool:
    source = Path(str(row.get("_source_artifact", ""))).name.lower()
    return source.startswith("smoke") or "smoke" in source


def _reward(row: dict[str, Any]) -> float:
    try:
        return float(row.get("reward", 0.0) or 0.0)
    except Exception:
        return 0.0


def _success(row: dict[str, Any]) -> bool:
    return _reward(row) > 0


def _rate(k: int, n: int) -> float | None:
    return k / n if n else None


def _wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> list[float | None]:
    if n <= 0:
        return [None, None]
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def _fmt(x: float | None) -> str:
    return "NA" if x is None else f"{x:.3f}"


def _latex_escape(value: Any) -> str:
    return (
        str(value)
        .replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
        .replace("_", "\\_")
    )


def summarize_baseline(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        if row.get("condition") == "baseline":
            groups[(str(row.get("env")), str(row.get("model")), str(row.get("provider")))].append(row)
    out: list[dict[str, Any]] = []
    for (env, model, provider), items in sorted(groups.items()):
        ok_items = [r for r in items if r.get("status") == "ok"]
        success = sum(1 for r in ok_items if _success(r))
        out.append(
            {
                "env": env,
                "model": model,
                "provider": provider,
                "planned_or_seen": len(items),
                "ok": len(ok_items),
                "failed": sum(1 for r in items if r.get("status") == "failed"),
                "provider_error": sum(1 for r in items if r.get("status") == "provider_error"),
                "timeout": sum(1 for r in items if r.get("status") == "timeout"),
                "skipped": sum(1 for r in items if r.get("status") == "skipped"),
                "baseline_success_count": success,
                "baseline_success_rate": _rate(success, len(ok_items)),
                "mean_reward": sum(_reward(r) for r in ok_items) / len(ok_items) if ok_items else None,
                "status_label": _baseline_status_label(success),
            }
        )
    return out


def _baseline_status_label(success_count: int) -> str:
    if success_count >= 20:
        return "main_ready"
    if success_count >= 15:
        return "usable"
    if success_count >= 5:
        return "exploratory"
    return "insufficient"


def _baseline_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("env"),
        row.get("model"),
        row.get("provider"),
        row.get("task_id", row.get("task_index")),
        row.get("seed"),
    )


def baseline_audit_payload(rows: list[dict[str, Any]], inputs: list[Path]) -> dict[str, Any]:
    latest = _latest([r for r in rows if r.get("condition") == "baseline" and not r.get("fake_run")])
    groups = summarize_baseline(latest)
    ok_rows = [r for r in latest if r.get("status") == "ok"]
    rewards = [_reward(r) for r in ok_rows]
    baseline_good = [r for r in ok_rows if _success(r)]
    unstable = [
        r
        for r in latest
        if r.get("status") in {"failed", "timeout", "provider_error"}
        or (r.get("status") == "ok" and not _success(r))
    ]
    task_coverage: dict[str, dict[str, Any]] = {}
    for r in latest:
        key = f"{r.get('env')}|{r.get('model')}"
        entry = task_coverage.setdefault(key, {"tasks_seen": set(), "seeds_seen": set(), "cells": 0})
        entry["tasks_seen"].add(r.get("task_id", r.get("task_index")))
        entry["seeds_seen"].add(r.get("seed"))
        entry["cells"] += 1
    task_coverage_out = {
        key: {
            "task_count": len(value["tasks_seen"]),
            "seed_count": len(value["seeds_seen"]),
            "cells": value["cells"],
            "tasks": sorted(x for x in value["tasks_seen"] if x is not None),
        }
        for key, value in sorted(task_coverage.items())
    }
    status_counts = collections.Counter(str(r.get("status") or "unknown") for r in latest)
    return {
        "inputs": [str(p) for p in inputs],
        "warnings": [] if latest else ["no real baseline status rows found; run baseline shards first"],
        "total_baseline_cells": len(latest),
        "status_counts": dict(sorted(status_counts.items())),
        "ok": status_counts.get("ok", 0),
        "failed": status_counts.get("failed", 0),
        "timeout": status_counts.get("timeout", 0),
        "provider_error": status_counts.get("provider_error", 0),
        "skipped": status_counts.get("skipped", 0),
        "baseline_success_count": len(baseline_good),
        "baseline_success_rate": _rate(len(baseline_good), len(ok_rows)),
        "mean_reward": sum(rewards) / len(rewards) if rewards else None,
        "per_env_model_provider": groups,
        "task_coverage": task_coverage_out,
        "baseline_good_cells": [
            {
                "cell_key": r.get("cell_key"),
                "env": r.get("env"),
                "model": r.get("model"),
                "provider": r.get("provider"),
                "task_id": r.get("task_id", r.get("task_index")),
                "seed": r.get("seed"),
                "reward": _reward(r),
            }
            for r in sorted(baseline_good, key=_baseline_key)
        ],
        "unstable_cells": [
            {
                "cell_key": r.get("cell_key"),
                "env": r.get("env"),
                "model": r.get("model"),
                "provider": r.get("provider"),
                "task_id": r.get("task_id", r.get("task_index")),
                "seed": r.get("seed"),
                "status": r.get("status"),
                "reward": _reward(r) if r.get("status") == "ok" else None,
                "error_message": r.get("error_message"),
            }
            for r in sorted(unstable, key=_baseline_key)
        ],
    }


def summarize_observability(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        if row.get("status") != "ok":
            continue
        if row.get("mutation_name") != "C4_business_rule_drift":
            continue
        level = row.get("observability_level")
        if level not in OBSERVABILITY_LEVELS:
            continue
        if row.get("baseline_success") is False:
            continue
        groups[(str(row.get("env")), str(row.get("model")), str(level))].append(row)
    out: list[dict[str, Any]] = []
    for (env, model, level), items in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1], observability_order(kv[0][2]))):
        n = len(items)
        success = sum(1 for r in items if _success(r))
        baseline_rewards = [float(r.get("baseline_reward") or 1.0) for r in items]
        drops = [b - _reward(r) for b, r in zip(baseline_rewards, items)]
        out.append(
            {
                "env": env,
                "model": model,
                "observability_level": level,
                "paired_baseline_successful_count": n,
                "success_count": success,
                "success_rate": _rate(success, n),
                "success_wilson_ci": _wilson_ci(success, n),
                "mean_drop": sum(drops) / n if n else None,
                "recovery_attempted_rate": _rate(sum(1 for r in items if r.get("recovery_attempted")), n),
                "recovery_success_rate": _rate(sum(1 for r in items if r.get("recovery_success")), n),
                "visible_policy_error_rate": _rate(sum(1 for r in items if r.get("visible_policy_error")), n),
                "hidden_business_rule_violation_rate": _rate(sum(1 for r in items if r.get("hidden_business_rule_violation")), n),
                "failure_mode_distribution": dict(collections.Counter(str(r.get("failure_mode") or "none") for r in items)),
            }
        )
    return out


def summarize_bd(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        if row.get("status") != "ok":
            continue
        if row.get("mutation_class") not in {"B", "D"}:
            continue
        if row.get("baseline_success") is False:
            continue
        groups[
            (
                str(row.get("env")),
                str(row.get("model")),
                str(row.get("mutation_class")),
                str(row.get("mutation_name")),
                str(row.get("protocol")),
            )
        ].append(row)
    out: list[dict[str, Any]] = []
    for (env, model, cls, mutation, protocol), items in sorted(groups.items()):
        n = len(items)
        success = sum(1 for r in items if _success(r))
        out.append(
            {
                "env": env,
                "model": model,
                "mutation_class": cls,
                "mutation_name": mutation,
                "protocol": protocol,
                "paired_count": n,
                "success_count": success,
                "success_rate": _rate(success, n),
                "visible_error_rate": _rate(sum(1 for r in items if r.get("visible_policy_error")), n),
                "timeout_rate": _rate(sum(1 for r in items if r.get("timeout")), n),
                "failure_mode_distribution": dict(collections.Counter(str(r.get("failure_mode") or "none") for r in items)),
            }
        )
    return out


def uplift_summary(obs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_series: dict[tuple[str, str], dict[str, dict[str, Any]]] = collections.defaultdict(dict)
    for row in obs:
        by_series[(row["env"], row["model"])][row["observability_level"]] = row
    out: list[dict[str, Any]] = []
    for (env, model), levels in sorted(by_series.items()):
        o0 = levels.get("O0_silent")
        if not o0 or o0.get("success_rate") is None:
            continue
        for level in ["O2_policy_error", "O3_structured_policy_error", "O4_migration_note"]:
            row = levels.get(level)
            if not row or row.get("success_rate") is None:
                continue
            uplift = float(row["success_rate"]) - float(o0["success_rate"])
            out.append(
                {
                    "env": env,
                    "model": model,
                    "contrast": f"{level}-O0_silent",
                    "uplift": uplift,
                    "n_level": row["paired_baseline_successful_count"],
                    "n_o0": o0["paired_baseline_successful_count"],
                }
            )
    return out


def write_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Phase 5 Summary",
        "",
        f"- inputs: {payload['inputs']}",
        f"- raw rows: {payload['raw_rows']}",
        f"- latest rows: {payload['latest_rows']}",
        f"- fake rows excluded: {payload['fake_rows_excluded']}",
        f"- warnings: {payload['warnings']}",
        "",
        "## Baseline Selection",
        "| env | model | provider | ok | baseline success | success rate | provider errors | timeout |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in payload["baseline_selection"]:
        lines.append(
            f"| {row['env']} | {row['model']} | {row['provider']} | {row['ok']} | "
            f"{row['baseline_success_count']} | {_fmt(row['baseline_success_rate'])} | "
            f"{row['provider_error']} | {row['timeout']} |"
        )
    if not payload["baseline_selection"]:
        lines.append("| NA | NA | NA | 0 | 0 | NA | 0 | 0 |")
    lines.extend(
        [
            "",
            "## Observability Gradient",
            "| env | model | level | paired | success | mean drop | recovery success | visible error | hidden violation |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in payload["observability_gradient"]:
        lines.append(
            f"| {row['env']} | {row['model']} | {row['observability_level']} | "
            f"{row['paired_baseline_successful_count']} | {_fmt(row['success_rate'])} | "
            f"{_fmt(row['mean_drop'])} | {_fmt(row['recovery_success_rate'])} | "
            f"{_fmt(row['visible_policy_error_rate'])} | {_fmt(row['hidden_business_rule_violation_rate'])} |"
        )
    if not payload["observability_gradient"]:
        lines.append("| NA | NA | NA | 0 | NA | NA | NA | NA | NA |")
    lines.extend(
        [
            "",
            "## B/D Mutation Summary",
            "| env | model | class | mutation | protocol | paired | success | visible error |",
            "|---|---|---|---|---|---:|---:|---:|",
        ]
    )
    for row in payload["bd_mutations"]:
        lines.append(
            f"| {row['env']} | {row['model']} | {row['mutation_class']} | {row['mutation_name']} | "
            f"{row['protocol']} | {row['paired_count']} | {_fmt(row['success_rate'])} | {_fmt(row['visible_error_rate'])} |"
        )
    if not payload["bd_mutations"]:
        lines.append("| NA | NA | NA | NA | NA | 0 | NA | NA |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_baseline_audit_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Phase 5 Baseline Audit",
        "",
        f"- inputs: {payload['inputs']}",
        f"- warnings: {payload['warnings']}",
        f"- total baseline cells: {payload['total_baseline_cells']}",
        f"- ok / failed / timeout / provider_error / skipped: "
        f"{payload['ok']} / {payload['failed']} / {payload['timeout']} / "
        f"{payload['provider_error']} / {payload['skipped']}",
        f"- baseline success count: {payload['baseline_success_count']}",
        f"- baseline success rate: {_fmt(payload['baseline_success_rate'])}",
        f"- mean reward: {_fmt(payload['mean_reward'])}",
        "",
        "## Env / Model / Provider",
        "| Env | Model | Provider | Baseline cells | Success | Success rate | Timeout | Provider error | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in payload["per_env_model_provider"]:
        lines.append(
            f"| {row['env']} | {row['model']} | {row['provider']} | {row['planned_or_seen']} | "
            f"{row['baseline_success_count']} | {_fmt(row['baseline_success_rate'])} | "
            f"{row['timeout']} | {row['provider_error']} | {row['status_label']} |"
        )
    if not payload["per_env_model_provider"]:
        lines.append("| NA | NA | NA | 0 | 0 | NA | 0 | 0 | insufficient |")
    lines.extend(["", "## Task Coverage"])
    if payload["task_coverage"]:
        for key, value in payload["task_coverage"].items():
            lines.append(
                f"- {key}: tasks={value['task_count']}, seeds={value['seed_count']}, cells={value['cells']}"
            )
    else:
        lines.append("- no real baseline task coverage yet")
    lines.extend(
        [
            "",
            "## Baseline-Good Cells",
            f"- count: {len(payload['baseline_good_cells'])}",
            "",
            "## Unstable Cells",
            f"- count: {len(payload['unstable_cells'])}",
        ]
    )
    for cell in payload["unstable_cells"][:50]:
        lines.append(
            f"- {cell['env']} {cell['model']} task={cell['task_id']} seed={cell['seed']} "
            f"status={cell['status']} reward={cell['reward']} err={str(cell.get('error_message') or '')[:120]}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_baseline_audit_tex(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "% Auto-generated by code/schema_mutation/summarize_phase5.py --baseline-only",
        "\\begin{tabular}{lllrrrrrl}",
        "\\hline",
        "Env & Model & Provider & Cells & Success & Rate & Timeout & Provider error & Status \\\\",
        "\\hline",
    ]
    for row in payload["per_env_model_provider"]:
        lines.append(
            f"{_latex_escape(row['env'])} & {_latex_escape(row['model'].split('/')[-1])} & "
            f"{_latex_escape(row['provider'])} & {row['planned_or_seen']} & "
            f"{row['baseline_success_count']} & {_fmt(row['baseline_success_rate'])} & "
            f"{row['timeout']} & {row['provider_error']} & {_latex_escape(row['status_label'])} \\\\"
        )
    if not payload["per_env_model_provider"]:
        lines.append("NA & NA & NA & 0 & 0 & NA & 0 & 0 & insufficient \\\\")
    lines.extend(["\\hline", "\\end{tabular}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_obs_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "% Auto-generated by code/schema_mutation/summarize_phase5.py",
        "\\begin{tabular}{lllrrrr}",
        "\\hline",
        "Env & Model & Obs. & N & Success & Drop & Rec. \\\\",
        "\\hline",
    ]
    for row in rows:
        lines.append(
            f"{_latex_escape(row['env'])} & {_latex_escape(row['model'].split('/')[-1])} & "
            f"{_latex_escape(row['observability_level'])} & {row['paired_baseline_successful_count']} & "
            f"{_fmt(row['success_rate'])} & {_fmt(row['mean_drop'])} & {_fmt(row['recovery_success_rate'])} \\\\"
        )
    if not rows:
        lines.append("NA & NA & NA & 0 & NA & NA & NA \\\\")
    lines.extend(["\\hline", "\\end{tabular}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_bd_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    by_mut: dict[tuple[str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        by_mut[(row["mutation_class"], row["mutation_name"])].append(row)
    lines = [
        "% Auto-generated by code/schema_mutation/summarize_phase5.py",
        "\\begin{tabular}{llrrr}",
        "\\hline",
        "Class & Mutation & N & Success & Visible \\\\",
        "\\hline",
    ]
    for (cls, mutation), items in sorted(by_mut.items()):
        n = sum(int(r["paired_count"]) for r in items)
        success = sum(int(r["success_count"]) for r in items)
        visible_num = sum((r["visible_error_rate"] or 0) * int(r["paired_count"]) for r in items)
        lines.append(
            f"{_latex_escape(cls)} & {_latex_escape(mutation)} & {n} & {_fmt(_rate(success, n))} & {_fmt(_rate(round(visible_num), n))} \\\\"
        )
    if not by_mut:
        lines.append("NA & NA & 0 & NA & NA \\\\")
    lines.extend(["\\hline", "\\end{tabular}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_gradient_plot(path: Path, rows: list[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable; skipping gradient plot: {exc}")
        return
    if not rows:
        print("[warn] no observability rows; skipping gradient plot")
        if path.exists():
            path.unlink()
        return
    by_series: dict[tuple[str, str], dict[str, float]] = collections.defaultdict(dict)
    for row in rows:
        if row["success_rate"] is not None:
            by_series[(row["env"], row["model"])][row["observability_level"]] = row["success_rate"]
    if not by_series:
        print("[warn] no success rates; skipping gradient plot")
        return
    markers = ["o", "s", "^", "D", "x", "+", "v", "*"]
    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    xs = list(range(len(OBSERVABILITY_LEVELS)))
    for i, ((env, model), values) in enumerate(sorted(by_series.items())):
        ys = [values.get(level, float("nan")) for level in OBSERVABILITY_LEVELS]
        ax.plot(xs, ys, marker=markers[i % len(markers)], color=str(0.15 + 0.7 * (i / max(1, len(by_series) - 1))), linewidth=1.2, label=f"{env}:{model.split('/')[-1]}")
    ax.set_xticks(xs)
    ax.set_xticklabels(["O0", "O1", "O2", "O3", "O4"])
    ax.set_ylim(-0.02, 1.02)
    ax.set_ylabel("Task success rate")
    ax.set_xlabel("Semantic observability level")
    ax.grid(True, axis="y", color="0.85", linewidth=0.6)
    ax.legend(fontsize=7, frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def write_uplift_plot(path: Path, rows: list[dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable; skipping uplift plot: {exc}")
        return
    if not rows:
        print("[warn] no uplift rows; skipping uplift plot")
        if path.exists():
            path.unlink()
        return
    labels = [f"{r['env']}:{r['model'].split('/')[-1]} {r['contrast'].split('_')[0]}" for r in rows]
    ys = list(range(len(rows)))
    xs = [r["uplift"] for r in rows]
    fig_h = max(3.0, 0.24 * len(rows))
    fig, ax = plt.subplots(figsize=(7.0, fig_h))
    ax.scatter(xs, ys, marker="o", color="0.2")
    ax.axvline(0, color="0.5", linewidth=0.8)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=6)
    ax.set_xlabel("Success-rate uplift vs O0")
    ax.grid(True, axis="x", color="0.85", linewidth=0.6)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="*", help="Status JSONL files; default: runs/schema_mutation/phase5/status/*.jsonl")
    parser.add_argument("--include-fake", action="store_true", help="include local_fake smoke rows")
    parser.add_argument("--include-smoke", action="store_true", help="include smoke/smoke_live rows in formal Phase 5 summary")
    parser.add_argument("--baseline-only", action="store_true", help="write baseline audit artifacts only")
    parser.add_argument("--overwrite", action="store_true", help="overwrite formal Phase 5 summary/table/figure artifacts")
    parser.add_argument(
        "--baseline-glob",
        default="runs/schema_mutation/phase5/status/baseline_*_status.jsonl",
        help="Glob for baseline status files used by --baseline-only.",
    )
    parser.add_argument(
        "--audit-prefix",
        default="baseline",
        help="Output prefix for --baseline-only artifacts; default keeps historical baseline_audit names.",
    )
    args = parser.parse_args()

    if args.baseline_only:
        pattern = Path(args.baseline_glob)
        if pattern.is_absolute():
            inputs = sorted(pattern.parent.glob(pattern.name))
        else:
            inputs = sorted(_REPO_ROOT.glob(str(pattern).replace("\\", "/")))
        raw_rows: list[dict[str, Any]] = []
        for path in inputs:
            raw_rows.extend(_read_jsonl(path))
        payload = baseline_audit_payload(raw_rows, inputs)
        RUNS.mkdir(parents=True, exist_ok=True)
        prefix = args.audit_prefix.strip() or "baseline"
        out_json = RUNS / f"{prefix}_audit.json"
        out_md = RUNS / f"{prefix}_audit.md"
        out_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_baseline_audit_md(out_md, payload)
        tables = PAPER / "tables"
        tables.mkdir(parents=True, exist_ok=True)
        if prefix == "baseline":
            out_tex = tables / "phase5_baseline_audit_auto.tex"
        else:
            out_tex = tables / f"{prefix}_audit_auto.tex"
        write_baseline_audit_tex(out_tex, payload)
        print(f"baseline_audit_json={out_json}")
        print(f"baseline_audit_md={out_md}")
        print(f"baseline_audit_tex={out_tex}")
        for warning in payload["warnings"]:
            print(f"[warn] {warning}")
        return 0

    inputs = [Path(p) if Path(p).is_absolute() else _REPO_ROOT / p for p in args.inputs]
    if not inputs:
        inputs = sorted((RUNS / "status").glob("*.jsonl"))
    raw_rows: list[dict[str, Any]] = []
    for path in inputs:
        raw_rows.extend(_read_jsonl(path))
    fake_count = sum(1 for r in raw_rows if r.get("fake_run"))
    smoke_count = sum(1 for r in raw_rows if _is_smoke(r))
    rows = raw_rows
    if not args.include_fake:
        rows = [r for r in rows if not r.get("fake_run")]
    if not args.include_smoke:
        rows = [r for r in rows if not _is_smoke(r)]
    latest = _latest(rows)
    warnings: list[str] = []
    if fake_count and not args.include_fake:
        warnings.append(f"excluded {fake_count} local_fake smoke rows")
    if smoke_count and not args.include_smoke:
        warnings.append(f"excluded {smoke_count} smoke rows")
    if not latest:
        warnings.append("no real Phase 5 status rows available yet")

    baseline = summarize_baseline(latest)
    obs = summarize_observability(latest)
    bd = summarize_bd(latest)
    uplifts = uplift_summary(obs)
    payload = {
        "inputs": [str(p) for p in inputs],
        "raw_rows": len(raw_rows),
        "latest_rows": len(latest),
        "fake_rows_excluded": 0 if args.include_fake else fake_count,
        "smoke_rows_excluded": 0 if args.include_smoke else smoke_count,
        "warnings": warnings,
        "baseline_selection": baseline,
        "observability_gradient": obs,
        "bd_mutations": bd,
        "observability_uplift": uplifts,
    }

    RUNS.mkdir(parents=True, exist_ok=True)
    out_json = RUNS / "phase5_summary.json"
    out_md = RUNS / "phase5_summary.md"
    formal_outputs_exist = out_json.exists() or out_md.exists()
    write_formal = args.overwrite or not formal_outputs_exist
    if not write_formal:
        warnings.append("formal summary exists; writing phase5_summary_preview.* and not updating paper tables/figures without --overwrite")
        out_json = RUNS / "phase5_summary_preview.json"
        out_md = RUNS / "phase5_summary_preview.md"
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_md(out_md, payload)

    tables = PAPER / "tables"
    figures = PAPER / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    obs_tex = tables / "observability_gradient_auto.tex"
    bd_tex = tables / "bd_mutation_summary_auto.tex"
    gradient_pdf = figures / "observability_gradient_curve.pdf"
    uplift_pdf = figures / "observability_uplift_forest.pdf"
    if write_formal:
        write_obs_tex(obs_tex, obs)
        write_bd_tex(bd_tex, bd)
        write_gradient_plot(gradient_pdf, obs)
        write_uplift_plot(uplift_pdf, uplifts)

    print(f"summary_json={out_json}")
    print(f"summary_md={out_md}")
    if write_formal:
        print(f"observability_tex={obs_tex}")
        print(f"bd_tex={bd_tex}")
        if gradient_pdf.exists():
            print(f"gradient_pdf={gradient_pdf}")
        if uplift_pdf.exists():
            print(f"uplift_pdf={uplift_pdf}")
    if warnings:
        for warning in warnings:
            print(f"[warn] {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
