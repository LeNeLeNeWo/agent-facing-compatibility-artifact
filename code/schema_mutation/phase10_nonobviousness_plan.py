"""Plan Phase 10 non-obviousness control cells without executing APIs.

The plan tests whether O0 silent drift is solved merely by more reasoning or
reflection. It reuses existing O0 hidden-violation cells as matched references
and creates only plan/shard files. No model calls are made here.
"""

from __future__ import annotations

import collections
import hashlib
import json
import random
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PHASE5_STATUS = ROOT / "runs" / "schema_mutation" / "phase5" / "status"
OUT_DIR = ROOT / "runs" / "schema_mutation" / "phase10" / "nonobviousness"
SHARD_DIR = OUT_DIR / "shards"
FORMAL_MODELS = {
    "deepseek/deepseek-v4-flash",
    "dashscope/qwen-max",
    "dashscope/kimi-k2.6",
    "dashscope/glm-5.1",
}


CONDITIONS = {
    "O0_increased_reasoning_budget": {
        "observability_level": "O0_silent",
        "max_num_steps": 80,
        "timeout_seconds": 900,
        "runner_ready": True,
        "agent_prompt_variant": "standard",
        "description": "O0 silent drift with a larger action budget; no new semantic rule is provided.",
    },
    "O0_reflection_scaffold": {
        "observability_level": "O0_silent",
        "max_num_steps": 60,
        "timeout_seconds": 900,
        "runner_ready": False,
        "agent_prompt_variant": "reflection_scaffold",
        "description": "O0 silent drift with a future reflection/plan-and-check prompt hook; no changed rule is provided.",
    },
    "rule_in_tool_preamble_upper_bound": {
        "observability_level": "O4_migration_note",
        "max_num_steps": 30,
        "timeout_seconds": 600,
        "runner_ready": True,
        "agent_prompt_variant": "rule_visible_preamble",
        "description": "Upper-bound condition using the existing O4 migration-note/tool-preamble visibility path.",
    },
}


DRIFT_BY_CLASS = {
    "C1": "Unit/scale drift: the target tool now interprets numeric values using a changed unit or scale while schema remains unchanged.",
    "C2": "Currency/locale drift: the target tool now interprets currency, locale, or regional defaults differently while schema remains unchanged.",
    "C3": "Default-behavior drift: omitted optional fields now trigger a changed default behavior while schema remains unchanged.",
    "C4": "Business-rule drift: the target tool now enforces a changed eligibility, payment, refund, or policy rule while schema remains unchanged.",
}


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


def semantic_class(row: dict[str, Any]) -> str:
    if row.get("semantic_class"):
        return str(row["semantic_class"])
    mutation = str(row.get("mutation_name") or "")
    if mutation.startswith("C1"):
        return "C1"
    if mutation.startswith("C2"):
        return "C2"
    if mutation.startswith("C3"):
        return "C3"
    if mutation.startswith("C4"):
        return "C4"
    return "C4"


def load_o0_hidden() -> list[dict[str, Any]]:
    paths = []
    patterns = [
        "observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl",
        "airline_observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl",
        "c_semantic_generalization_[0-9][0-9][0-9][0-9]_status.jsonl",
    ]
    for pattern in patterns:
        paths.extend(PHASE5_STATUS.glob(pattern))
    rows: list[dict[str, Any]] = []
    for path in sorted(paths):
        if "smoke" in path.name or "retry" in path.name:
            continue
        for row in read_jsonl(path):
            if row.get("status") != "ok":
                continue
            if row.get("fake_run") is True:
                continue
            if row.get("baseline_success") is not True:
                continue
            if row.get("observability_level") != "O0_silent":
                continue
            if row.get("hidden_business_rule_violation") is not True:
                continue
            if row.get("model") not in FORMAL_MODELS:
                continue
            if str(row.get("provider") or "").lower() in {"wyzlab", "wyzai"}:
                continue
            row = dict(row)
            row["_source_artifact"] = str(path.relative_to(ROOT))
            rows.append(row)
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        latest[str(row.get("cell_key"))] = row
    return list(latest.values())


def h(*parts: Any) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:12]


def select_base(rows: list[dict[str, Any]], target: int = 96, seed: int = 1010) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    by_bucket: dict[tuple[str, str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        by_bucket[(str(row.get("env")), str(row.get("model")), semantic_class(row))].append(row)
    selected: list[dict[str, Any]] = []
    keys = sorted(by_bucket)
    while len(selected) < target and keys:
        progressed = False
        for key in list(keys):
            bucket = by_bucket[key]
            if not bucket:
                keys.remove(key)
                continue
            rng.shuffle(bucket)
            selected.append(bucket.pop())
            progressed = True
            if len(selected) >= target:
                break
        if not progressed:
            break
    selected.sort(key=lambda r: (semantic_class(r), str(r.get("env")), str(r.get("model")), int(r.get("task_id")), int(r.get("seed"))))
    return selected


def make_cell(base: dict[str, Any], condition: str) -> dict[str, Any]:
    spec = CONDITIONS[condition]
    cls = semantic_class(base)
    mutation = base.get("mutation_name") or "C4_business_rule_drift"
    target_tool = base.get("target_tool")
    drift = base.get("business_rule_drift") or DRIFT_BY_CLASS.get(cls, DRIFT_BY_CLASS["C4"])
    return {
        "phase": "phase10",
        "experiment": "nonobviousness_control",
        "cell_key": f"p10_nonobv_{h(base.get('cell_key'), condition)}",
        "env": base.get("env"),
        "model": base.get("model"),
        "provider": base.get("provider"),
        "task_id": int(base.get("task_id")),
        "seed": int(base.get("seed")),
        "condition": condition,
        "condition_family": "nonobviousness_control",
        "observability_level": spec["observability_level"],
        "mutation_class": "C",
        "semantic_class": cls,
        "mutation_name": mutation,
        "protocol": "intent_aligned",
        "target_tool": target_tool,
        "target_tools": [target_tool] if target_tool else [],
        "baseline_success": True,
        "schema_changed": False,
        "typed_client_compatible": True,
        "source_o0_cell_key": base.get("cell_key"),
        "source_baseline_cell_key": base.get("source_baseline_cell_key"),
        "source_artifact": base.get("_source_artifact"),
        "known_o0_hidden_violation": True,
        "business_rule_intent": base.get("business_rule_intent") or cls.lower(),
        "business_rule_drift": drift,
        "max_num_steps": spec["max_num_steps"],
        "timeout_seconds": spec["timeout_seconds"],
        "agent_prompt_variant": spec["agent_prompt_variant"],
        "runner_ready": spec["runner_ready"],
        "requires_runner_extension": not spec["runner_ready"],
        "rationale": spec["description"],
    }


def make_plan() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    base_rows = select_base(load_o0_hidden(), target=96)
    plan: list[dict[str, Any]] = []
    for base in base_rows:
        for condition in CONDITIONS:
            plan.append(make_cell(base, condition))
    plan.sort(key=lambda r: (r["condition"], r["semantic_class"], r["env"], r["model"], r["task_id"], r["seed"]))
    return base_rows, plan


def make_shards(plan: list[dict[str, Any]], shard_size: int = 40) -> list[Path]:
    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for old in SHARD_DIR.glob("nonobviousness_*.jsonl"):
        old.unlink()
    for i in range(0, len(plan), shard_size):
        shard = plan[i : i + shard_size]
        path = SHARD_DIR / f"nonobviousness_{i // shard_size:04d}.jsonl"
        write_jsonl(path, shard)
        paths.append(path)
    return paths


def make_smoke(plan: list[dict[str, Any]]) -> Path:
    # Include two domains, at least two models, and all three conditions.
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in plan:
        key = (row["env"], row["model"], row["condition"])
        if key in seen:
            continue
        selected.append(row)
        seen.add(key)
        if len(selected) >= 18:
            break
    path = SHARD_DIR / "nonobviousness_smoke.jsonl"
    write_jsonl(path, selected)
    return path


def summarize(base_rows: list[dict[str, Any]], plan: list[dict[str, Any]], shards: list[Path], smoke: Path) -> dict[str, Any]:
    runner_ready = [r for r in plan if r["runner_ready"]]
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "baseline_reference_cells": len(base_rows),
        "planned_cells": len(plan),
        "runner_ready_cells": len(runner_ready),
        "requires_runner_extension_cells": len(plan) - len(runner_ready),
        "expected_new_api_calls_if_all_conditions_run": len(plan),
        "expected_new_api_calls_runner_ready_only": len(runner_ready),
        "by_condition": dict(collections.Counter(r["condition"] for r in plan)),
        "by_env": dict(collections.Counter(r["env"] for r in plan)),
        "by_model": dict(collections.Counter(r["model"] for r in plan)),
        "by_semantic_class": dict(collections.Counter(r["semantic_class"] for r in plan)),
        "smoke_shard": str(smoke.relative_to(ROOT)),
        "formal_shards": [str(p.relative_to(ROOT)) for p in shards],
        "stop_rules": [
            "provider_error >= 5 in one shard",
            "timeout >= 5 in one shard",
            "failed >= 10 in one shard",
            "fake_run appears",
            "GPT/WYZ/Grok appears",
            "schema_changed=true appears",
            "baseline_success=false appears",
        ],
        "metrics": [
            "success rate by condition",
            "hidden_business_rule_violation rate",
            "visible_policy_error/migration_note rates",
            "delta from matched O0 reference",
        ],
        "note": "Reflection scaffold rows are planned but require a runner prompt hook before execution.",
    }


def write_report(summary: dict[str, Any]) -> None:
    (OUT_DIR / "nonobviousness_control_plan_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Phase 10A Non-Obviousness Control Plan",
        "",
        "No API calls were run. This plan tests whether silent semantic drift can be solved by more reasoning without exposing the changed rule.",
        "",
        f"- Baseline O0 hidden-positive reference cells: {summary['baseline_reference_cells']}",
        f"- Planned cells: {summary['planned_cells']}",
        f"- Runner-ready cells: {summary['runner_ready_cells']}",
        f"- Rows requiring runner prompt hook: {summary['requires_runner_extension_cells']}",
        f"- Expected API calls if all conditions run: {summary['expected_new_api_calls_if_all_conditions_run']}",
        f"- Expected API calls for runner-ready subset: {summary['expected_new_api_calls_runner_ready_only']}",
        f"- Smoke shard: `{summary['smoke_shard']}`",
        "",
        "## By Condition",
    ]
    for k, v in sorted(summary["by_condition"].items()):
        lines.append(f"- {k}: {v}")
    lines += ["", "## By Domain"]
    for k, v in sorted(summary["by_env"].items()):
        lines.append(f"- {k}: {v}")
    lines += ["", "## By Model"]
    for k, v in sorted(summary["by_model"].items()):
        lines.append(f"- {k}: {v}")
    lines += ["", "## By Semantic Class"]
    for k, v in sorted(summary["by_semantic_class"].items()):
        lines.append(f"- {k}: {v}")
    lines += [
        "",
        "## How This Addresses the Obviousness Critique",
        "",
        "The matched design keeps the same O0 hidden semantic drift cells and varies only reasoning budget, reflection scaffolding, or explicit rule visibility. If larger budgets and reflection do not recover while rule visibility does, the failure is not merely weak reasoning; it is missing semantic observability.",
        "",
        "## Stop Rules",
    ]
    for item in summary["stop_rules"]:
        lines.append(f"- {item}")
    lines += ["", f"Note: {summary['note']}"]
    (OUT_DIR / "nonobviousness_control_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "nonobviousness_plan_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SHARD_DIR.mkdir(parents=True, exist_ok=True)
    base_rows, plan = make_plan()
    write_jsonl(OUT_DIR / "nonobviousness_control_plan.jsonl", plan)
    shards = make_shards(plan)
    smoke = make_smoke(plan)
    summary = summarize(base_rows, plan, shards, smoke)
    write_report(summary)
    print(f"base={len(base_rows)} plan={len(plan)} smoke={smoke} shards={len(shards)}")
    return 0 if len(base_rows) >= 80 else 2


if __name__ == "__main__":
    raise SystemExit(main())
