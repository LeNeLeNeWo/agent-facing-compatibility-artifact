"""Generic pilot runner: orchestrates conditions × items, writes raw + summary.

每个 pilot 只需要：
1. 定义 ``conditions: dict[str, Callable[[item], str]]`` （condition_name → 推理函数）
2. 调用 ``run_pilot(items, conditions, scorer, output_dir)``

Runner 自动处理：
- 并发 item 调度（默认 8 worker，可通过 PILOT_N_WORKERS env 调整）
- 每个 (condition, item) 写入 raw.jsonl
- 计算 condition 间的 compare() + verdict
- 输出 summary.json + report.md
"""
from __future__ import annotations

import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from tqdm import tqdm

from .stats import compare, verdict


def _to_dict(x: Any) -> Any:
    if is_dataclass(x):
        return asdict(x)
    if isinstance(x, (list, tuple)):
        return [_to_dict(v) for v in x]
    if isinstance(x, dict):
        return {k: _to_dict(v) for k, v in x.items()}
    return x


def run_pilot(
    items: list[Any],
    conditions: dict[str, Callable[[Any], str]],
    scorer: Callable[[Any, str], int],
    output_dir: str | Path,
    *,
    pilot_name: str = "pilot",
    extra_meta: Optional[dict[str, Any]] = None,
    baseline_condition: Optional[str] = None,
    n_workers: Optional[int] = None,
) -> dict[str, Any]:
    """Run all conditions on all items and produce raw / summary / report.

    Args:
        items:       list of dataclass / dict instances; passed to each condition fn.
        conditions:  name -> fn(item) -> candidate_answer_string
        scorer:      fn(item, candidate) -> 0/1
        output_dir:  results root; a timestamped subdir is created inside.
        baseline_condition:
                     if set, every other condition is compared against this one.
                     If None, conditions are pairwise-compared (n*(n-1)/2 pairs).
        n_workers:   并发处理 item 的线程数，默认 8 / 或读 PILOT_N_WORKERS env。
                     条件 fn 内部一般是 LLM API 调用，I/O bound，多线程有效。
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(output_dir) / f"runs/{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    raw_path = run_dir / "raw.jsonl"
    cond_scores: dict[str, list[tuple[int, int]]] = {name: [] for name in conditions}
    started = time.time()

    workers = int(n_workers if n_workers is not None
                  else os.getenv("PILOT_N_WORKERS", "4"))
    workers = max(1, min(workers, len(items)))

    print(f"[runner] {pilot_name}: {len(items)} items × {len(conditions)} conditions "
          f"(workers={workers})")
    print(f"[runner] writing to: {run_dir}")

    write_lock = threading.Lock()

    def _process_one(idx: int, item: Any) -> tuple[int, dict[str, Any], dict[str, int]]:
        row: dict[str, Any] = {"item": _to_dict(item)}
        scores_for_item: dict[str, int] = {}
        for cond_name, cond_fn in conditions.items():
            t0 = time.time()
            try:
                cand = cond_fn(item)
                err = None
            except Exception as e:  # noqa: BLE001
                cand = ""
                err = str(e)
            latency = time.time() - t0
            score = scorer(item, cand) if err is None else 0
            scores_for_item[cond_name] = score
            row[cond_name] = {
                "answer": cand,
                "score": score,
                "latency_s": round(latency, 3),
                "error": err,
            }
        return idx, row, scores_for_item

    rows_buffer: dict[int, dict[str, Any]] = {}

    with raw_path.open("w", encoding="utf-8") as fout, \
            ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_process_one, i, it): i for i, it in enumerate(items)}
        with tqdm(total=len(items), desc=pilot_name) as pbar:
            for fut in as_completed(futures):
                idx, row, scores_for_item = fut.result()
                with write_lock:
                    for name, s in scores_for_item.items():
                        cond_scores[name].append((idx, s))
                    rows_buffer[idx] = row
                    # 按 idx 顺序 flush 已就绪的连续行（保证 raw.jsonl 顺序稳定）
                    next_idx = sum(1 for k in rows_buffer if k < len(items))
                pbar.update(1)
        # 写入：按 idx 顺序导出
        for i in range(len(items)):
            if i in rows_buffer:
                fout.write(json.dumps(rows_buffer[i], ensure_ascii=False) + "\n")
        fout.flush()

    elapsed = time.time() - started

    # 提取 score 列表（按 idx 排序后丢掉 idx）
    cond_score_lists: dict[str, list[int]] = {
        name: [s for _, s in sorted(pairs)] for name, pairs in cond_scores.items()
    }

    # --- per-condition summary ---
    per_cond = {
        name: {
            "n": len(scores),
            "accuracy": (sum(scores) / len(scores)) if scores else float("nan"),
        }
        for name, scores in cond_score_lists.items()
    }

    # --- pairwise comparisons ---
    comps: list[dict[str, Any]] = []
    cond_names = list(conditions.keys())
    if baseline_condition and baseline_condition in cond_names:
        for name in cond_names:
            if name == baseline_condition:
                continue
            r = compare(cond_score_lists[name], cond_score_lists[baseline_condition],
                        name_a=name, name_b=baseline_condition)
            comps.append({**r.to_dict(), "verdict": verdict(r)})
    else:
        for i, na in enumerate(cond_names):
            for nb in cond_names[i + 1:]:
                r = compare(cond_score_lists[na], cond_score_lists[nb], name_a=na, name_b=nb)
                comps.append({**r.to_dict(), "verdict": verdict(r)})

    summary = {
        "pilot": pilot_name,
        "timestamp": ts,
        "n_items": len(items),
        "conditions": list(conditions.keys()),
        "elapsed_seconds": round(elapsed, 1),
        "n_workers": workers,
        "per_condition": per_cond,
        "comparisons": comps,
        "meta": extra_meta or {},
    }

    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- report.md ---
    lines = [
        f"# Pilot Report · {pilot_name}",
        "",
        f"- timestamp: {ts}",
        f"- n_items: {len(items)}",
        f"- elapsed: {elapsed:.1f}s",
        f"- workers: {workers}",
        "",
        "## Per-condition accuracy",
        "",
        "| condition | n | accuracy |",
        "|---|---|---|",
    ]
    for name, info in per_cond.items():
        acc = info["accuracy"]
        lines.append(f"| {name} | {info['n']} | {acc:.3f} |")
    lines += ["", "## Pairwise comparisons", "",
              "| A | B | mean_A | mean_B | Δ | 95% CI | Cohen's d | p | verdict |",
              "|---|---|---|---|---|---|---|---|---|"]
    for c in comps:
        lines.append(
            f"| {c['name_a']} | {c['name_b']} | {c['mean_a']:.3f} | {c['mean_b']:.3f} | "
            f"{c['delta']:+.3f} | [{c['ci_lo']:+.3f}, {c['ci_hi']:+.3f}] | "
            f"{c['cohens_d']:+.2f} | {c['p_value']:.3f} | **{c['verdict']}** |"
        )
    (run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"[runner] DONE · summary: {run_dir / 'summary.json'}")
    print(f"[runner] report:  {run_dir / 'report.md'}")
    return summary

