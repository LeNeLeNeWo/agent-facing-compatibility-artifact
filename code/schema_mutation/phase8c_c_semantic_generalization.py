"""Plan and summarize Phase 8C C1-C3 semantic-class generalization.

This script intentionally reuses only frozen Phase 5 baseline-successful O0
cells and creates runtime-only schema-invisible C1/C2/C3 semantic drifts. It
does not execute model calls; execution is delegated to run_phase5_shard.py.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import random
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PHASE5_STATUS = ROOT / "runs" / "schema_mutation" / "phase5" / "status"
OUT_DIR = ROOT / "runs" / "schema_mutation" / "phase8" / "c_semantic_generalization"
SHARD_DIR = OUT_DIR / "shards"
TABLE_DIR = ROOT / "IEEE_Conference_Template" / "tables"
FIG_DIR = ROOT / "IEEE_Conference_Template" / "figures"

FORMAL_MODELS = {
    "deepseek/deepseek-v4-flash",
    "dashscope/qwen-max",
    "dashscope/kimi-k2.6",
    "dashscope/glm-5.1",
}
FORMAL_PROVIDERS = {"deepseek", "dashscope"}
SEMANTIC_CLASSES = {
    "C1": {
        "mutation_name": "C1_unit_scale_drift",
        "intent": "unit_scale",
        "rule": (
            "Unit/scale drift: the target tool now interprets numeric amounts, "
            "weights, quantities, or fees using a different unit or scale while "
            "the endpoint and JSON schema remain unchanged."
        ),
    },
    "C2": {
        "mutation_name": "C2_currency_locale_drift",
        "intent": "currency_locale",
        "rule": (
            "Currency/locale drift: the target tool now interprets currency, "
            "locale, regional, or date-like values using a different default "
            "locale while the endpoint and JSON schema remain unchanged."
        ),
    },
    "C3": {
        "mutation_name": "C3_default_behavior_drift",
        "intent": "default_behavior",
        "rule": (
            "Default-behavior drift: when an optional field is omitted, the "
            "target tool now applies a different default behavior while the "
            "endpoint and JSON schema remain unchanged."
        ),
    },
}
LEVELS = ["O0_silent", "O3_structured_policy_error"]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def cell_hash(parts: list[Any]) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def latest_by_key(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("cell_key") or "")
        if key:
            latest[key] = row
    return latest


def load_exposed_o0() -> list[dict[str, Any]]:
    paths = list(PHASE5_STATUS.glob("observability_from_baseline_*_status.jsonl"))
    paths += list(PHASE5_STATUS.glob("airline_observability_from_baseline_*_status.jsonl"))
    rows: list[dict[str, Any]] = []
    for path in paths:
        name = path.name
        if "smoke" in name or "retry" in name:
            continue
        for row in read_jsonl(path):
            if row.get("status") != "ok":
                continue
            if row.get("observability_level") != "O0_silent":
                continue
            if row.get("baseline_success") is not True:
                continue
            if row.get("provider") not in FORMAL_PROVIDERS:
                continue
            if row.get("model") not in FORMAL_MODELS:
                continue
            if str(row.get("provider") or "").lower().startswith("wyz"):
                continue
            if any(x in str(row.get("model") or "").lower() for x in ("gpt", "grok", "wyz")):
                continue
            if row.get("fake_run") is True:
                continue
            if not row.get("target_tool"):
                continue
            rows.append(row)
    # Deduplicate retry/appended rows defensively.
    rows = list(latest_by_key(rows).values())
    rows.sort(key=lambda r: (str(r.get("env")), str(r.get("model")), int(r.get("task_id")), int(r.get("seed"))))
    return rows


def select_base_rows(rows: list[dict[str, Any]], per_model: int, retail_min_per_model: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    by_model: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        by_model[str(row.get("model"))].append(row)

    selected: list[dict[str, Any]] = []
    for model in sorted(FORMAL_MODELS):
        candidates = list(by_model.get(model, []))
        retail = [r for r in candidates if r.get("env") == "retail"]
        airline = [r for r in candidates if r.get("env") == "airline"]
        rng.shuffle(retail)
        rng.shuffle(airline)
        take_retail = min(retail_min_per_model, len(retail), per_model)
        picked = retail[:take_retail]
        remaining = per_model - len(picked)
        picked += airline[:remaining]
        if len(picked) < per_model:
            leftovers = [r for r in candidates if r not in picked]
            rng.shuffle(leftovers)
            picked += leftovers[: per_model - len(picked)]
        if len(picked) < per_model:
            raise RuntimeError(f"not enough exposed O0 rows for {model}: {len(picked)}/{per_model}")
        selected.extend(picked)
    selected.sort(key=lambda r: (str(r.get("model")), str(r.get("env")), int(r.get("task_id")), int(r.get("seed"))))
    return selected


def make_cell(base: dict[str, Any], semantic_class: str, level: str) -> dict[str, Any]:
    spec = SEMANTIC_CLASSES[semantic_class]
    h = cell_hash([
        "phase8c",
        base.get("cell_key"),
        semantic_class,
        level,
        base.get("model"),
        base.get("task_id"),
        base.get("seed"),
    ])
    condition = f"{semantic_class}_{level}"
    drift = f"{spec['rule']} Changed tool: {base.get('target_tool')}."
    return {
        "phase": "phase8c",
        "experiment": "c_semantic_generalization",
        "cell_key": f"p8c_{h}",
        "env": base.get("env"),
        "model": base.get("model"),
        "provider": base.get("provider"),
        "task_id": int(base.get("task_id")),
        "seed": int(base.get("seed")),
        "condition": condition,
        "mutation_class": "C",
        "semantic_class": semantic_class,
        "mutation_name": spec["mutation_name"],
        "observability_level": level,
        "protocol": "intent_aligned",
        "changed_tool": base.get("target_tool"),
        "target_tool": base.get("target_tool"),
        "target_tools": [base.get("target_tool")],
        "changed_rule": drift,
        "business_rule_intent": spec["intent"],
        "business_rule_drift": drift,
        "schema_changed": False,
        "typed_client_compatible": True,
        "baseline_success": True,
        "expected_exposure": True,
        "source_baseline_cell_key": base.get("cell_key"),
        "source_exposed_o0_cell_key": base.get("cell_key"),
        "max_num_steps": 30,
        "timeout_seconds": 600,
        "rationale": (
            f"Runtime-only {semantic_class} schema-invisible semantic drift on "
            f"baseline-exposed tool {base.get('target_tool')}."
        ),
    }


def generate_plan(args: argparse.Namespace) -> list[dict[str, Any]]:
    exposed = load_exposed_o0()
    if len(exposed) < 300:
        raise RuntimeError(f"expected at least 300 frozen exposed O0 rows, found {len(exposed)}")
    plan: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    for idx, cls in enumerate(SEMANTIC_CLASSES):
        try:
            selected = select_base_rows(
                exposed,
                per_model=args.per_model,
                retail_min_per_model=args.retail_min_per_model,
                seed=args.seed + idx,
            )
        except Exception as exc:  # noqa: BLE001
            unmatched.append({"semantic_class": cls, "reason": str(exc)})
            continue
        for base in selected:
            for level in LEVELS:
                plan.append(make_cell(base, cls, level))

    plan.sort(key=lambda c: (c["semantic_class"], c["model"], c["env"], c["task_id"], c["seed"], c["observability_level"]))
    write_jsonl(OUT_DIR / "c_semantic_generalization_plan.jsonl", plan)
    write_jsonl(OUT_DIR / "c_semantic_generalization_unmatched.jsonl", unmatched)
    write_plan_md(plan, unmatched, len(exposed), args)
    make_shards(plan, args.shard_size)
    make_smoke_shard(exposed)
    return plan


def counter(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(collections.Counter(str(r.get(key)) for r in rows))


def write_plan_md(plan: list[dict[str, Any]], unmatched: list[dict[str, Any]], exposed_count: int, args: argparse.Namespace) -> None:
    lines = [
        "# Phase 8C C1-C3 Semantic-Class Generalization Plan",
        "",
        f"- frozen_exposed_o0_rows_available: {exposed_count}",
        f"- planned_formal_cells: {len(plan)}",
        f"- expected_api_calls_formal: {len(plan)}",
        f"- expected_api_calls_smoke: 12",
        f"- unmatched_specs: {len(unmatched)}",
        f"- per_model_per_class_base_cells: {args.per_model}",
        f"- retail_min_per_model_per_class: {args.retail_min_per_model}",
        "- observability_levels: O0_silent, O3_structured_policy_error",
        "- schema_changed: false for all planned cells",
        "- typed_client_compatible: true for all planned cells",
        "- excluded providers/models: WYZ/GPT/Grok",
        "",
        "## Cells by Semantic Class",
    ]
    for k, v in counter(plan, "semantic_class").items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Cells by Observability Level")
    for k, v in counter(plan, "observability_level").items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Cells by Domain")
    for k, v in counter(plan, "env").items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Cells by Model")
    for k, v in counter(plan, "model").items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Exclusion / Stop Notes")
    lines.append("- If planned formal cells are below 300, do not execute API calls.")
    lines.append("- Provider errors, timeouts, failed rows, fake rows, schema_changed rows, and baseline_failed rows are excluded from analysis.")
    lines.append("- This plan only covers C1/C2/C3 semantic-contract changes; no A/B/D mutations are planned.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "c_semantic_generalization_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_shards(plan: list[dict[str, Any]], shard_size: int) -> None:
    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    for old in SHARD_DIR.glob("c_semantic_generalization_*.jsonl"):
        if old.name != "c_semantic_generalization_smoke.jsonl":
            old.unlink()
    for i in range(0, len(plan), shard_size):
        shard = plan[i : i + shard_size]
        write_jsonl(SHARD_DIR / f"c_semantic_generalization_{i // shard_size:04d}.jsonl", shard)


def make_smoke_shard(exposed: list[dict[str, Any]]) -> None:
    smoke: list[dict[str, Any]] = []
    models = sorted(FORMAL_MODELS)
    for cls_idx, cls in enumerate(SEMANTIC_CLASSES):
        # Pick one retail and one airline base row, rotating models where possible.
        picks: list[dict[str, Any]] = []
        for env in ("retail", "airline"):
            preferred = models[(cls_idx + len(picks)) % len(models)]
            candidates = [r for r in exposed if r.get("env") == env and r.get("model") == preferred]
            if not candidates:
                candidates = [r for r in exposed if r.get("env") == env]
            if candidates:
                picks.append(candidates[0])
        for j, base in enumerate(picks[:2]):
            for level in LEVELS:
                cell = make_cell(base, cls, level)
                cell["cell_key"] = cell["cell_key"] + f"_smoke{j}"
                cell["condition"] = cell["condition"] + "_smoke"
                smoke.append(cell)
    write_jsonl(SHARD_DIR / "c_semantic_generalization_smoke.jsonl", smoke)


def rate(rows: list[dict[str, Any]], field: str) -> float | None:
    if not rows:
        return None
    if field == "success":
        return sum(1 for r in rows if float(r.get("reward") or 0.0) > 0) / len(rows)
    return sum(1 for r in rows if bool(r.get(field))) / len(rows)


def bootstrap_diff(a: list[float], b: list[float], rounds: int = 2000, seed: int = 8) -> dict[str, Any]:
    if not a or not b:
        return {"point": None, "ci": [None, None], "rounds": rounds}
    rng = random.Random(seed)
    point = mean(b) - mean(a)
    vals = []
    for _ in range(rounds):
        aa = [rng.choice(a) for _ in a]
        bb = [rng.choice(b) for _ in b]
        vals.append(mean(bb) - mean(aa))
    vals.sort()
    lo = vals[int(0.025 * (len(vals) - 1))]
    hi = vals[int(0.975 * (len(vals) - 1))]
    return {"point": point, "ci": [lo, hi], "rounds": rounds}


def fisher_p(a_success: int, a_fail: int, b_success: int, b_fail: int) -> dict[str, Any]:
    try:
        from scipy.stats import fisher_exact  # type: ignore

        odds, p = fisher_exact([[a_success, a_fail], [b_success, b_fail]])
        return {"odds_ratio": odds, "p_value": p}
    except Exception:
        return {"odds_ratio": None, "p_value": None}


def load_formal_results() -> list[dict[str, Any]]:
    paths = sorted(PHASE5_STATUS.glob("c_semantic_generalization_[0-9][0-9][0-9][0-9]_status.jsonl"))
    paths += sorted(PHASE5_STATUS.glob("c_semantic_generalization_retry*_status.jsonl"))
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(read_jsonl(path))
    return list(latest_by_key(rows).values())


def summarize_results() -> dict[str, Any]:
    rows_all = load_formal_results()
    rows = [
        r for r in rows_all
        if r.get("status") == "ok"
        and r.get("baseline_success") is True
        and r.get("fake_run") is not True
        and r.get("provider") in FORMAL_PROVIDERS
        and r.get("model") in FORMAL_MODELS
        and r.get("schema_changed") is False
    ]
    integrity = {
        "completed_rows_latest": len(rows_all),
        "ok": sum(1 for r in rows_all if r.get("status") == "ok"),
        "provider_error": sum(1 for r in rows_all if r.get("status") == "provider_error"),
        "timeout": sum(1 for r in rows_all if r.get("status") == "timeout"),
        "failed": sum(1 for r in rows_all if r.get("status") == "failed"),
        "formal_rows_after_filters": len(rows),
        "no_gpt_wyz_grok": not any(any(x in str(r.get("model") or "").lower() for x in ("gpt", "grok", "wyz")) or str(r.get("provider") or "").lower().startswith("wyz") for r in rows),
        "schema_changed_rows": sum(1 for r in rows_all if r.get("schema_changed") is True),
        "baseline_failed_rows": sum(1 for r in rows_all if r.get("baseline_success") is False),
    }

    by_class: dict[str, Any] = {}
    for cls in SEMANTIC_CLASSES:
        cls_rows = [r for r in rows if r.get("semantic_class") == cls]
        o0 = [r for r in cls_rows if r.get("observability_level") == "O0_silent"]
        vis = [r for r in cls_rows if r.get("observability_level") == "O3_structured_policy_error"]
        o0_success = [1.0 if float(r.get("reward") or 0.0) > 0 else 0.0 for r in o0]
        vis_success = [1.0 if float(r.get("reward") or 0.0) > 0 else 0.0 for r in vis]
        uplift = bootstrap_diff(o0_success, vis_success)
        o0_s = sum(o0_success)
        v_s = sum(vis_success)
        fisher = fisher_p(int(o0_s), len(o0) - int(o0_s), int(v_s), len(vis) - int(v_s))
        by_class[cls] = {
            "mutation_name": SEMANTIC_CLASSES[cls]["mutation_name"],
            "total_n": len(cls_rows),
            "o0_n": len(o0),
            "visible_n": len(vis),
            "o0_success_rate": rate(o0, "success"),
            "visible_success_rate": rate(vis, "success"),
            "o0_hidden_violation_rate": rate(o0, "hidden_business_rule_violation"),
            "visible_hidden_violation_rate": rate(vis, "hidden_business_rule_violation"),
            "visible_policy_error_rate": rate(vis, "visible_policy_error"),
            "uplift_visible_minus_o0": uplift["point"],
            "uplift_ci": uplift["ci"],
            "fisher_exact": fisher,
        }

    by_domain: dict[str, Any] = {}
    for env in sorted({str(r.get("env")) for r in rows}):
        by_domain[env] = {}
        for cls in SEMANTIC_CLASSES:
            subset = [r for r in rows if r.get("env") == env and r.get("semantic_class") == cls]
            by_domain[env][cls] = {
                "n": len(subset),
                "o0_success_rate": rate([r for r in subset if r.get("observability_level") == "O0_silent"], "success"),
                "visible_success_rate": rate([r for r in subset if r.get("observability_level") == "O3_structured_policy_error"], "success"),
            }
    by_model: dict[str, Any] = {}
    for model in sorted({str(r.get("model")) for r in rows}):
        by_model[model] = {}
        for cls in SEMANTIC_CLASSES:
            subset = [r for r in rows if r.get("model") == model and r.get("semantic_class") == cls]
            by_model[model][cls] = {
                "n": len(subset),
                "o0_success_rate": rate([r for r in subset if r.get("observability_level") == "O0_silent"], "success"),
                "visible_success_rate": rate([r for r in subset if r.get("observability_level") == "O3_structured_policy_error"], "success"),
            }

    summary = {
        "integrity": integrity,
        "by_class": by_class,
        "by_domain": by_domain,
        "by_model": by_model,
        "main_answer": {
            "c1_c3_produce_schema_compatible_agent_facing_regressions": all((by_class[c]["o0_hidden_violation_rate"] or 0) > 0 for c in SEMANTIC_CLASSES),
            "visible_feedback_helps_beyond_c4": all((by_class[c]["uplift_visible_minus_o0"] or 0) > 0 for c in SEMANTIC_CLASSES),
            "direction_consistent_enough_for_c_class_generalization": all((by_class[c]["uplift_visible_minus_o0"] or 0) > 0 for c in SEMANTIC_CLASSES),
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "c_semantic_generalization_review_packet.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_review_md(summary)
    write_tex_table(summary)
    write_figure(summary)
    return summary


def pct(x: float | None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{100*x:.1f}%"


def signed_pp(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{100*x:+.1f} pp"


def write_review_md(summary: dict[str, Any]) -> None:
    lines = ["# Phase 8C C1-C3 Semantic-Class Generalization Review", ""]
    lines.append("## Integrity")
    for k, v in summary["integrity"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Overall by Semantic Class")
    lines.append("| Class | O0 N | O0 Success | Visible N | Visible Success | O0 Hidden | Visible Hidden | Uplift | 95% CI | Fisher p |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for cls, row in summary["by_class"].items():
        ci = row["uplift_ci"]
        p = row["fisher_exact"]["p_value"]
        lines.append(
            f"| {cls} | {row['o0_n']} | {pct(row['o0_success_rate'])} | "
            f"{row['visible_n']} | {pct(row['visible_success_rate'])} | "
            f"{pct(row['o0_hidden_violation_rate'])} | {pct(row['visible_hidden_violation_rate'])} | "
            f"{signed_pp(row['uplift_visible_minus_o0'])} | "
            f"[{signed_pp(ci[0])}, {signed_pp(ci[1])}] | "
            f"{p:.3g} |"
        )
    lines.append("")
    lines.append("## By Domain")
    for env, data in summary["by_domain"].items():
        lines.append(f"### {env}")
        for cls, row in data.items():
            lines.append(
                f"- {cls}: N={row['n']}, O0={pct(row['o0_success_rate'])}, "
                f"visible={pct(row['visible_success_rate'])}"
            )
    lines.append("")
    lines.append("## By Model")
    for model, data in summary["by_model"].items():
        lines.append(f"### {model}")
        for cls, row in data.items():
            lines.append(
                f"- {cls}: N={row['n']}, O0={pct(row['o0_success_rate'])}, "
                f"visible={pct(row['visible_success_rate'])}"
            )
    lines.append("")
    lines.append("## Main Answer")
    for k, v in summary["main_answer"].items():
        lines.append(f"- {k}: {v}")
    (OUT_DIR / "c_semantic_generalization_review_packet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(s: str) -> str:
    return s.replace("_", "\\_")


def write_tex_table(summary: dict[str, Any]) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\scriptsize",
        "\\caption{C1--C3 semantic-class generalization. Visible feedback uses O3 structured policy errors; the table is generated for review and is not included automatically in the main paper.}",
        "\\label{tab:c-semantic-generalization}",
        "\\begin{tabular}{lrrrrrr}",
        "\\toprule",
        "Class & O0 N & O0 Succ. & Vis. N & Vis. Succ. & Uplift & Hidden Drop \\\\",
        "\\midrule",
    ]
    for cls, row in summary["by_class"].items():
        hidden_drop = None
        if row["o0_hidden_violation_rate"] is not None and row["visible_hidden_violation_rate"] is not None:
            hidden_drop = row["o0_hidden_violation_rate"] - row["visible_hidden_violation_rate"]
        lines.append(
            f"{tex_escape(cls)} & {row['o0_n']} & {pct(row['o0_success_rate'])} & "
            f"{row['visible_n']} & {pct(row['visible_success_rate'])} & "
            f"{signed_pp(row['uplift_visible_minus_o0'])} & {signed_pp(hidden_drop)} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    (TABLE_DIR / "c_semantic_generalization_auto.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_figure(summary: dict[str, Any]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    classes = list(SEMANTIC_CLASSES)
    o0 = [summary["by_class"][c]["o0_success_rate"] for c in classes]
    vis = [summary["by_class"][c]["visible_success_rate"] for c in classes]
    xs = range(len(classes))
    fig, ax = plt.subplots(figsize=(3.4, 2.15))
    ax.plot(xs, o0, marker="o", color="0.15", linestyle="-", label="O0 silent")
    ax.plot(xs, vis, marker="s", color="0.55", linestyle="--", label="O3 visible")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(classes)
    ax.set_ylim(0, 1.02)
    ax.set_ylabel("Task success rate")
    ax.grid(axis="y", color="0.88", linewidth=0.6)
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout(pad=0.3)
    fig.savefig(FIG_DIR / "c_semantic_generalization.pdf")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-plan", action="store_true")
    parser.add_argument("--summarize", action="store_true")
    parser.add_argument("--per-model", type=int, default=20)
    parser.add_argument("--retail-min-per-model", type=int, default=6)
    parser.add_argument("--shard-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=8)
    args = parser.parse_args()
    if not args.generate_plan and not args.summarize:
        args.generate_plan = True
    if args.generate_plan:
        plan = generate_plan(args)
        print(f"planned_formal_cells={len(plan)}")
        print(f"plan={OUT_DIR / 'c_semantic_generalization_plan.jsonl'}")
    if args.summarize:
        summary = summarize_results()
        print(json.dumps(summary["integrity"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
