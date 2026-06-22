"""Compute C4a/C4b observability statistics and generate paper artifacts.

The script is deliberately conservative: retail counts are recovered only from
paired JSONL artifacts that contain baseline_reward and mutation_reward fields.
Airline counts use the day16 final summary, which is the authoritative summary
artifact for the reported 17 DeepSeek and 4 Qwen-max paired records.
"""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs" / "schema_mutation"
PAPER = ROOT / "IEEE_Conference_Template"
if not PAPER.exists():
    PAPER = Path("<PROJECT_ROOT>/IEEE_Conference_Template")

OUT_JSON = RUNS / "c4_observability_stats.json"
OUT_MD = RUNS / "c4_observability_stats.md"
OUT_TEX = PAPER / "tables" / "c4_observability_auto.tex"
OUT_FIG = PAPER / "figures" / "c4_observability_gap.pdf"

RETAIL_FILES = [
    RUNS / "paired_day10_c4a_c4b_deepseek.jsonl",
    RUNS / "paired_day11_c4a_c4b_qwen_kimi.jsonl",
]
AIRLINE_SUMMARY = RUNS / "day16_airline_final_summary.json"

MODEL_LABELS = {
    "deepseek/deepseek-v4-flash": "DeepSeek",
    "dashscope/qwen3.7-max-2026-06-08": "Qwen-max",
    "dashscope/kimi-k2.6": "Kimi",
}

MODEL_ORDER = {
    ("retail", "deepseek/deepseek-v4-flash"): 0,
    ("retail", "dashscope/qwen3.7-max-2026-06-08"): 1,
    ("retail", "dashscope/kimi-k2.6"): 2,
    ("airline", "deepseek/deepseek-v4-flash"): 3,
    ("airline", "dashscope/qwen3.7-max-2026-06-08"): 4,
}


def model_label(env: str, model: str) -> str:
    if env == "retail" and model == "dashscope/qwen3.7-max-2026-06-08":
        return "Qwen"
    return MODEL_LABELS.get(model, model)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)
                row["_source"] = str(path.relative_to(ROOT))
                rows.append(row)
    return rows


def success(row: dict[str, Any]) -> bool:
    return float(row.get("mutation_reward", row.get("reward", 0)) or 0) > 0


def mode_of(row: dict[str, Any]) -> str | None:
    mode = str(row.get("c4_runtime_mode") or "").lower()
    label = str(row.get("label") or "").lower()
    if mode == "visible" or "c4a" in label or "visible" in label:
        return "visible"
    if mode == "silent" or "c4b" in label or "silent" in label:
        return "silent"
    return None


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> list[float | None]:
    if n <= 0:
        return [None, None]
    phat = k / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return [max(0.0, center - half), min(1.0, center + half)]


def exact_mcnemar_p(b: int, c: int) -> float | None:
    n = b + c
    if n == 0:
        return None
    tail = sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / (2**n)
    return min(1.0, 2 * tail)


def percentile(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    pos = (len(xs) - 1) * p
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    return xs[lo] * (hi - pos) + xs[hi] * (pos - lo)


def task_clustered_gap_ci(records: list[dict[str, Any]], reps: int = 5000) -> list[float | None]:
    by_task: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_task[r.get("task_index")].append(r)
    tasks = list(by_task)
    if len(tasks) < 2:
        return [None, None]
    rng = random.Random(20260613)
    gaps = []
    for _ in range(reps):
        sample = []
        for _ in tasks:
            sample.extend(by_task[rng.choice(tasks)])
        vis = [r for r in sample if mode_of(r) == "visible"]
        sil = [r for r in sample if mode_of(r) == "silent"]
        if not vis or not sil:
            continue
        gaps.append(sum(success(r) for r in vis) / len(vis) - sum(success(r) for r in sil) / len(sil))
    return [percentile(gaps, 0.025), percentile(gaps, 0.975)]


def summarize_records(env: str, model: str, records: list[dict[str, Any]], source: str) -> dict[str, Any]:
    modes = {"visible": [], "silent": []}
    for r in records:
        if float(r.get("baseline_reward", 0) or 0) != 1.0:
            continue
        mode = mode_of(r)
        if mode in modes:
            modes[mode].append(r)

    cells: dict[tuple[Any, Any], dict[str, dict[str, Any]]] = defaultdict(dict)
    for mode, rs in modes.items():
        for r in rs:
            cells[(r.get("task_index"), r.get("seed"))][mode] = r
    both = {cell: v for cell, v in cells.items() if "visible" in v and "silent" in v}
    b = sum(1 for v in both.values() if success(v["visible"]) and not success(v["silent"]))
    c = sum(1 for v in both.values() if not success(v["visible"]) and success(v["silent"]))

    visible_n = len(modes["visible"])
    silent_n = len(modes["silent"])
    visible_k = sum(success(r) for r in modes["visible"])
    silent_k = sum(success(r) for r in modes["silent"])
    visible_rate = visible_k / visible_n if visible_n else None
    silent_rate = silent_k / silent_n if silent_n else None
    gap = visible_rate - silent_rate if visible_rate is not None and silent_rate is not None else None
    strict_gap = None
    if both:
        strict_gap = (
            sum(success(v["visible"]) for v in both.values()) / len(both)
            - sum(success(v["silent"]) for v in both.values()) / len(both)
        )

    warnings = []
    if visible_n != silent_n or len(both) != visible_n or len(both) != silent_n:
        warnings.append(
            f"condition totals are not identical: visible={visible_n}, silent={silent_n}, strict_common={len(both)}"
        )

    return {
        "env": env,
        "model": model,
        "model_label": model_label(env, model),
        "source": source,
        "visible": {
            "n": visible_n,
            "successes": visible_k,
            "rate": visible_rate,
            "wilson95": wilson_ci(visible_k, visible_n),
        },
        "silent": {
            "n": silent_n,
            "successes": silent_k,
            "rate": silent_rate,
            "wilson95": wilson_ci(silent_k, silent_n),
        },
        "gap": gap,
        "strict_common_cells": len(both),
        "strict_common_gap": strict_gap,
        "mcnemar": {"b_visible_success_silent_fail": b, "c_visible_fail_silent_success": c, "exact_p": exact_mcnemar_p(b, c)},
        "task_clustered_gap_ci": task_clustered_gap_ci(records) if env == "retail" else [None, None],
        "tasks": sorted({r.get("task_index") for r in records if "task_index" in r}),
        "seeds": sorted({r.get("seed") for r in records if "seed" in r}),
        "warnings": warnings,
    }


def collect_retail() -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    rows = []
    fields: dict[str, list[str]] = {}
    for path in RETAIL_FILES:
        file_rows = read_jsonl(path)
        fields[str(path.relative_to(ROOT))] = sorted({k for r in file_rows for k in r if not k.startswith("_")})
        for r in file_rows:
            r["_env"] = "retail"
            rows.append(r)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("mutation_type") == "C4_business_rule_drift":
            grouped[str(r.get("model"))].append(r)
    stats = [
        summarize_records("retail", model, records, "paired retail JSONL")
        for model, records in grouped.items()
    ]
    return stats, fields


def collect_airline() -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    if not AIRLINE_SUMMARY.exists():
        return [], {}
    data = json.loads(AIRLINE_SUMMARY.read_text(encoding="utf-8"))
    fields = {str(AIRLINE_SUMMARY.relative_to(ROOT)): sorted(data.keys())}
    by_model: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in data.get("summaries", []):
        mode = "visible" if row.get("mode") == "visible" else "silent"
        by_model[str(row.get("model"))][mode] = row

    stats = []
    for model, modes in by_model.items():
        if "visible" not in modes or "silent" not in modes:
            continue
        vis = modes["visible"]
        sil = modes["silent"]
        visible_n = int(vis["paired"])
        silent_n = int(sil["paired"])
        visible_k = int(round(float(vis["success"]) * visible_n))
        silent_k = int(round(float(sil["success"]) * silent_n))
        b = visible_k if silent_k == 0 else 0
        c = 0
        warnings = []
        if visible_n != silent_n:
            warnings.append(f"airline summary condition totals differ: visible={visible_n}, silent={silent_n}")
        if silent_k != 0:
            warnings.append("exact paired test not derived because silent successes are nonzero without cell-level pairing")
        stats.append(
            {
                "env": "airline",
                "model": model,
                "model_label": model_label("airline", model),
                "source": str(AIRLINE_SUMMARY.relative_to(ROOT)),
                "visible": {
                    "n": visible_n,
                    "successes": visible_k,
                    "rate": float(vis["success"]),
                    "wilson95": wilson_ci(visible_k, visible_n),
                    "bootstrap95": vis.get("success_ci_bootstrap"),
                },
                "silent": {
                    "n": silent_n,
                    "successes": silent_k,
                    "rate": float(sil["success"]),
                    "wilson95": wilson_ci(silent_k, silent_n),
                    "bootstrap95": sil.get("success_ci_bootstrap"),
                },
                "gap": float(vis["success"]) - float(sil["success"]),
                "strict_common_cells": min(visible_n, silent_n),
                "strict_common_gap": float(vis["success"]) - float(sil["success"]),
                "mcnemar": {
                    "b_visible_success_silent_fail": b,
                    "c_visible_fail_silent_success": c,
                    "exact_p": exact_mcnemar_p(b, c) if silent_k == 0 else None,
                    "note": "derived from paired summary and zero C4b successes",
                },
                "task_clustered_gap_ci": [None, None],
                "tasks": [],
                "seeds": [],
                "warnings": warnings,
            }
        )
    return stats, fields


def fmt_rate(k: int, n: int, rate: float | None) -> str:
    if rate is None:
        return "TODO-HIGH"
    return f"{k}/{n} ({rate:.3f})"


def fmt_ci(ci: list[float | None]) -> str:
    if not ci or ci[0] is None or ci[1] is None:
        return "TODO-HIGH"
    return f"[{ci[0]:.3f},{ci[1]:.3f}]"


def fmt_p(p: float | None) -> str:
    if p is None:
        return "TODO-HIGH"
    if p < 0.001:
        return "$p<0.001$"
    return f"$p={p:.3f}$"


def write_json_md_tex(stats: list[dict[str, Any]], fields: dict[str, list[str]]) -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    OUT_TEX.parent.mkdir(parents=True, exist_ok=True)
    payload = {"stats": stats, "discovered_fields": fields}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# C4 Observability Statistics",
        "",
        "Generated by `code/schema_mutation/stats_c4_observability.py`.",
        "",
        "| Env | Model | C4a n | C4a success | C4b n | C4b success | Gap | Strict common cells | Exact paired test | Notes |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for s in sorted(stats, key=lambda x: MODEL_ORDER.get((x["env"], x["model"]), 99)):
        notes = "; ".join(s.get("warnings", []))
        lines.append(
            f"| {s['env']} | {s['model_label']} | {s['visible']['n']} | "
            f"{fmt_rate(s['visible']['successes'], s['visible']['n'], s['visible']['rate'])} | "
            f"{s['silent']['n']} | {fmt_rate(s['silent']['successes'], s['silent']['n'], s['silent']['rate'])} | "
            f"{s['gap']:.3f} | {s['strict_common_cells']} | {fmt_p(s['mcnemar']['exact_p'])} | {notes} |"
        )
    lines += ["", "## Discovered Fields", ""]
    for source, fs in fields.items():
        lines.append(f"- `{source}`: {', '.join(fs)}")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tex = [
        "\\begin{table*}[t]",
        "\\caption{C4 observability gap across retail and airline. Retail counts are recovered from paired C4a/C4b JSONL artifacts; airline counts come from the day16 final summary. CIs are Wilson intervals unless marked bootstrap.}",
        "\\label{tab:c4-observability}",
        "\\centering",
        "\\scriptsize",
        "\\setlength{\\tabcolsep}{2pt}",
        "\\begin{tabularx}{\\textwidth}{p{0.09\\textwidth}p{0.12\\textwidth}p{0.11\\textwidth}p{0.14\\textwidth}p{0.14\\textwidth}p{0.07\\textwidth}X}",
        "\\toprule",
        "\\textbf{Env} & \\textbf{Model} & \\textbf{Records} & \\textbf{C4a success} & \\textbf{C4b success} & \\textbf{Gap} & \\textbf{CI / test} \\\\",
        "\\midrule",
    ]
    for s in sorted(stats, key=lambda x: MODEL_ORDER.get((x["env"], x["model"]), 99)):
        rec = f"{s['visible']['n']}/{s['silent']['n']}"
        vis = fmt_rate(s["visible"]["successes"], s["visible"]["n"], s["visible"]["rate"])
        sil = fmt_rate(s["silent"]["successes"], s["silent"]["n"], s["silent"]["rate"])
        if s["env"] == "airline" and "bootstrap95" in s["visible"]:
            ci_text = f"Bootstrap: {fmt_ci(s['visible']['bootstrap95'])} vs. {fmt_ci(s['silent']['bootstrap95'])}; exact {fmt_p(s['mcnemar']['exact_p'])}"
        else:
            ci_text = f"Wilson: {fmt_ci(s['visible']['wilson95'])} vs. {fmt_ci(s['silent']['wilson95'])}; exact {fmt_p(s['mcnemar']['exact_p'])}"
            if s.get("task_clustered_gap_ci", [None, None])[0] is not None:
                ci_text += f"; task-clustered gap {fmt_ci(s['task_clustered_gap_ci'])}"
        if s.get("warnings"):
            ci_text += "; note: strict common cells=" + str(s["strict_common_cells"])
        tex.append(
            f"{s['env'].title()} & {s['model_label']} & {rec} & {vis} & {sil} & {s['gap']:.3f} & {ci_text} \\\\"
        )
    tex += [
        "\\bottomrule",
        "\\end{tabularx}",
        "\\end{table*}",
        "",
    ]
    OUT_TEX.write_text("\n".join(tex), encoding="utf-8")


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def draw_text(parts: list[str], x: float, y: float, text: str, size: int = 8) -> None:
    parts.append(f"BT /F1 {size} Tf {x:.2f} {y:.2f} Td ({pdf_escape(text)}) Tj ET")


def draw_line(parts: list[str], x1: float, y1: float, x2: float, y2: float, width: float = 0.7, gray: float = 0.0) -> None:
    parts.append(f"{gray:.2f} G {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")


def draw_square(parts: list[str], x: float, y: float, r: float = 3.5, gray: float = 0.0) -> None:
    parts.append(f"{gray:.2f} g {gray:.2f} G {x-r:.2f} {y-r:.2f} {2*r:.2f} {2*r:.2f} re B")


def draw_circle(parts: list[str], x: float, y: float, r: float = 3.7, gray: float = 0.0) -> None:
    c = 0.5522847498 * r
    parts.append(
        f"{gray:.2f} G 0.8 w "
        f"{x+r:.2f} {y:.2f} m "
        f"{x+r:.2f} {y+c:.2f} {x+c:.2f} {y+r:.2f} {x:.2f} {y+r:.2f} c "
        f"{x-c:.2f} {y+r:.2f} {x-r:.2f} {y+c:.2f} {x-r:.2f} {y:.2f} c "
        f"{x-r:.2f} {y-c:.2f} {x-c:.2f} {y-r:.2f} {x:.2f} {y-r:.2f} c "
        f"{x+c:.2f} {y-r:.2f} {x+r:.2f} {y-c:.2f} {x+r:.2f} {y:.2f} c S"
    )


def write_pdf(path: Path, stats: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 520, 250
    left, right, bottom, top = 135, 32, 42, 26
    plot_w = width - left - right
    rows = sorted(stats, key=lambda x: MODEL_ORDER.get((x["env"], x["model"]), 99))
    y_gap = (height - top - bottom) / max(1, len(rows) - 1)

    def x_pos(rate: float) -> float:
        return left + rate * plot_w

    parts: list[str] = []
    draw_text(parts, 130, height - 15, "C4a vs. C4b observability gap", 10)
    draw_line(parts, left, bottom, left + plot_w, bottom, 0.8, 0.0)
    for t in [0, 0.25, 0.5, 0.75, 1.0]:
        x = x_pos(t)
        draw_line(parts, x, bottom, x, bottom - 4, 0.6, 0.0)
        draw_text(parts, x - 7, bottom - 17, f"{t:.2g}" if t not in [0, 1] else str(int(t)), 7)
        draw_line(parts, x, bottom, x, height - top + 8, 0.25, 0.85)
    draw_text(parts, left + plot_w / 2 - 30, 10, "Task success rate", 8)

    for i, s in enumerate(rows):
        y = height - top - i * y_gap
        label = f"{s['env'].title()} {s['model_label']}"
        draw_text(parts, 18, y - 3, label, 8)
        silent = float(s["silent"]["rate"])
        visible = float(s["visible"]["rate"])
        xs, xv = x_pos(silent), x_pos(visible)
        draw_line(parts, xs, y, xv, y, 1.0, 0.35)
        for rate, ci in [(silent, s["silent"].get("wilson95")), (visible, s["visible"].get("wilson95"))]:
            if ci and ci[0] is not None and ci[1] is not None:
                x1, x2 = x_pos(float(ci[0])), x_pos(float(ci[1]))
                draw_line(parts, x1, y, x2, y, 0.45, 0.55)
                draw_line(parts, x1, y - 3, x1, y + 3, 0.45, 0.55)
                draw_line(parts, x2, y - 3, x2, y + 3, 0.45, 0.55)
        draw_circle(parts, xs, y)
        draw_square(parts, xv, y)
        draw_text(parts, max(xs, xv) + 6, y - 3, f"gap {s['gap']:.3f}", 7)

    draw_circle(parts, left + 18, height - 235)
    draw_text(parts, left + 28, height - 238, "C4b silent", 7)
    draw_square(parts, left + 102, height - 235)
    draw_text(parts, left + 112, height - 238, "C4a visible", 7)

    content = "\n".join(parts).encode("ascii")
    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>".encode()
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode()
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(out)


def main() -> int:
    retail_stats, retail_fields = collect_retail()
    airline_stats, airline_fields = collect_airline()
    stats = sorted(retail_stats + airline_stats, key=lambda x: MODEL_ORDER.get((x["env"], x["model"]), 99))
    fields = {**retail_fields, **airline_fields}
    write_json_md_tex(stats, fields)
    write_pdf(OUT_FIG, stats)

    print("Discovered fields:")
    for source, fs in fields.items():
        print(f"- {source}: {', '.join(fs)}")
    print("\nC4 observability stats:")
    for s in stats:
        print(
            f"{s['env']} {s['model_label']}: "
            f"C4a={s['visible']['successes']}/{s['visible']['n']} ({s['visible']['rate']:.3f}), "
            f"C4b={s['silent']['successes']}/{s['silent']['n']} ({s['silent']['rate']:.3f}), "
            f"gap={s['gap']:.3f}, strict_common={s['strict_common_cells']}, "
            f"exact_p={s['mcnemar']['exact_p']}"
        )
        for warning in s.get("warnings", []):
            print(f"  warning: {warning}")
    print(f"\nwrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_TEX}")
    print(f"wrote {OUT_FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
