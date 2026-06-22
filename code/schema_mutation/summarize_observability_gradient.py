"""Summarize Phase 1 C4 observability-gradient JSONL outputs."""

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

from code.schema_mutation.c4_observability_modes import (  # noqa: E402
    OBSERVABILITY_LEVELS,
    observability_order,
)

RUNS = _REPO_ROOT / "runs" / "schema_mutation"
PAPER = _REPO_ROOT / "IEEE_Conference_Template"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        print(f"[warn] missing input: {path}")
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"[warn] {path}:{line_no}: {exc}")
    return rows


def _cell_key(r: dict[str, Any]) -> tuple[Any, ...]:
    return (
        r.get("env", "retail"),
        r.get("task_index"),
        r.get("model"),
        r.get("mutation_type"),
        r.get("seed"),
        r.get("target_policy", "random"),
        r.get("observability_level"),
        r.get("c4_runtime_mode"),
        r.get("max_num_steps"),
    )


def _base_key(r: dict[str, Any]) -> tuple[Any, ...]:
    return (r.get("env", "retail"), r.get("task_index"), r.get("model"), r.get("seed"))


def _reward(r: dict[str, Any]) -> float:
    return float(r.get("final_reward", r.get("reward", 0.0)) or 0.0)


def _success(r: dict[str, Any]) -> bool:
    return _reward(r) > 0


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


def _fmt_rate(x: float | None) -> str:
    return "NA" if x is None else f"{x:.3f}"


def _latest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[Any, ...], dict[str, Any]] = {}
    for r in rows:
        latest[_cell_key(r)] = r
    return list(latest.values())


def _summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baselines = {
        _base_key(r): r
        for r in rows
        if r.get("status") == "ok" and r.get("mutation_type") is None
    }
    baseline_good = {k: r for k, r in baselines.items() if _success(r)}
    groups: dict[tuple[str, str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = (
        collections.defaultdict(list)
    )

    for r in rows:
        if r.get("status") != "ok":
            continue
        if r.get("mutation_type") != "C4_business_rule_drift":
            continue
        level = r.get("observability_level")
        if level not in OBSERVABILITY_LEVELS:
            continue
        b = baseline_good.get(_base_key(r))
        if b is None:
            continue
        groups[(str(r.get("env", "retail")), str(r.get("model")), str(level))].append((r, b))

    summaries: list[dict[str, Any]] = []
    for (env_name, model, level), pairs in sorted(
        groups.items(), key=lambda x: (x[0][0], x[0][1], observability_order(x[0][2]))
    ):
        n = len(pairs)
        success_count = sum(1 for r, _ in pairs if _success(r))
        drops = [_reward(b) - _reward(r) for r, b in pairs]
        failure_modes = collections.Counter(str(r.get("failure_mode") or "unknown") for r, _ in pairs)
        rec_attempt = sum(1 for r, _ in pairs if r.get("recovery_attempted"))
        rec_success = sum(1 for r, _ in pairs if r.get("recovery_success"))
        visible = sum(1 for r, _ in pairs if r.get("visible_policy_error"))
        hidden = sum(1 for r, _ in pairs if r.get("hidden_business_rule_violation"))
        summaries.append(
            {
                "env": env_name,
                "model": model,
                "observability_level": level,
                "paired_baseline_successful_count": n,
                "success_count": success_count,
                "success_rate": _rate(success_count, n),
                "success_wilson_ci": _wilson_ci(success_count, n),
                "mean_drop": sum(drops) / n if n else None,
                "recovery_attempted_rate": _rate(rec_attempt, n),
                "recovery_success_rate": _rate(rec_success, n),
                "failure_mode_distribution": dict(sorted(failure_modes.items())),
                "visible_policy_error_rate": _rate(visible, n),
                "hidden_business_rule_violation_rate": _rate(hidden, n),
                "fake_rows": sum(1 for r, _ in pairs if r.get("fake_run")),
            }
        )
    return summaries


def _write_md(path: Path, summaries: list[dict[str, Any]], inputs: list[Path]) -> None:
    lines = [
        "# C4 Observability Gradient Summary",
        "",
        "Inputs:",
    ]
    lines.extend(f"- `{p}`" for p in inputs)
    lines.extend(
        [
            "",
            "| env | model | level | paired | success | Wilson 95% CI | mean drop | recovery attempted | recovery success | visible error | hidden violation | failure modes |",
            "|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for s in summaries:
        ci = s["success_wilson_ci"]
        modes = ", ".join(f"{k}:{v}" for k, v in s["failure_mode_distribution"].items())
        lines.append(
            f"| {s['env']} | {s['model']} | {s['observability_level']} | "
            f"{s['paired_baseline_successful_count']} | {_fmt_rate(s['success_rate'])} | "
            f"[{_fmt_rate(ci[0])}, {_fmt_rate(ci[1])}] | {_fmt_rate(s['mean_drop'])} | "
            f"{_fmt_rate(s['recovery_attempted_rate'])} | {_fmt_rate(s['recovery_success_rate'])} | "
            f"{_fmt_rate(s['visible_policy_error_rate'])} | "
            f"{_fmt_rate(s['hidden_business_rule_violation_rate'])} | {modes} |"
        )
    if not summaries:
        lines.append("| NA | NA | NA | 0 | NA | [NA, NA] | NA | NA | NA | NA | NA | no paired data |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _latex_escape(s: str) -> str:
    return (
        s.replace("\\", "\\textbackslash{}")
        .replace("_", "\\_")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("$", "\\$")
        .replace("#", "\\#")
    )


def _write_tex(path: Path, summaries: list[dict[str, Any]]) -> None:
    lines = [
        "% Auto-generated by code/schema_mutation/summarize_observability_gradient.py",
        "\\begin{tabular}{lllrrrr}",
        "\\hline",
        "Env & Model & Obs. & N & Success & Mean drop & Visible \\\\",
        "\\hline",
    ]
    for s in summaries:
        lines.append(
            f"{_latex_escape(s['env'])} & {_latex_escape(s['model'].split('/')[-1])} & "
            f"{_latex_escape(s['observability_level'])} & "
            f"{s['paired_baseline_successful_count']} & {_fmt_rate(s['success_rate'])} & "
            f"{_fmt_rate(s['mean_drop'])} & {_fmt_rate(s['visible_policy_error_rate'])} \\\\"
        )
    if not summaries:
        lines.append("NA & NA & NA & 0 & NA & NA & NA \\\\")
    lines.extend(["\\hline", "\\end{tabular}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_plot(path: Path, summaries: list[dict[str, Any]]) -> None:
    if not summaries:
        print("[warn] no paired data; skipping plot")
        if path.exists():
            path.unlink()
        return
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        print(f"[warn] matplotlib unavailable; skipping plot: {exc}")
        return

    by_series: dict[tuple[str, str], dict[str, float]] = collections.defaultdict(dict)
    for s in summaries:
        if s["success_rate"] is not None:
            by_series[(s["env"], s["model"])][s["observability_level"]] = s["success_rate"]
    if not by_series:
        print("[warn] no success rates; skipping plot")
        return

    markers = ["o", "s", "^", "D", "x", "+", "*", "v"]
    fig, ax = plt.subplots(figsize=(7.0, 3.4))
    xs = list(range(len(OBSERVABILITY_LEVELS)))
    for i, ((env_name, model), values) in enumerate(sorted(by_series.items())):
        ys = [values.get(level, float("nan")) for level in OBSERVABILITY_LEVELS]
        ax.plot(
            xs,
            ys,
            marker=markers[i % len(markers)],
            color=str(0.15 + 0.7 * (i / max(len(by_series) - 1, 1))),
            linewidth=1.2,
            label=f"{env_name}:{model.split('/')[-1]}",
        )
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "inputs",
        nargs="*",
        help="JSONL files; default glob: runs/schema_mutation/observability_gradient*.jsonl",
    )
    p.add_argument("--include-fake", action="store_true", help="include fake-run rows in summary")
    args = p.parse_args()

    inputs = [Path(x) for x in args.inputs]
    if not inputs:
        inputs = sorted(RUNS.glob("observability_gradient*.jsonl"))
    inputs = [p if p.is_absolute() else _REPO_ROOT / p for p in inputs]

    raw_rows: list[dict[str, Any]] = []
    for path in inputs:
        raw_rows.extend(_read_jsonl(path))
    if not args.include_fake:
        raw_rows = [r for r in raw_rows if not r.get("fake_run")]
    rows = _latest(raw_rows)
    summaries = _summarize(rows)

    RUNS.mkdir(parents=True, exist_ok=True)
    out_json = RUNS / "observability_gradient_summary.json"
    out_md = RUNS / "observability_gradient_summary.md"
    tables = PAPER / "tables"
    figures = PAPER / "figures"
    tables.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    out_tex = tables / "observability_gradient_auto.tex"
    out_pdf = figures / "observability_gradient_curve.pdf"

    out_json.write_text(
        json.dumps(
            {
                "inputs": [str(p) for p in inputs],
                "raw_rows": len(raw_rows),
                "latest_rows": len(rows),
                "summaries": summaries,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_md(out_md, summaries, inputs)
    _write_tex(out_tex, summaries)
    _write_plot(out_pdf, summaries)

    print(f"summary_json={out_json}")
    print(f"summary_md={out_md}")
    print(f"summary_tex={out_tex}")
    if out_pdf.exists():
        print(f"summary_pdf={out_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
