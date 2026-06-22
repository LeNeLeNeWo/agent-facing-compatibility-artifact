"""Plan Phase 5 large-scale schema-mutation experiments.

The plan is intentionally conservative: baseline selection is separated from
mutation execution, and mutation cells are marked as requiring baseline success.
Use ``--from-baseline-results`` after baseline shards finish to generate the
actual mutation shards for successful baseline cells only.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from code.schema_mutation.c4_observability_modes import OBSERVABILITY_LEVELS  # noqa: E402

RUNS = _REPO_ROOT / "runs" / "schema_mutation" / "phase5"
SHARDS = RUNS / "shards"

MAIN_MODELS = [
    ("deepseek/deepseek-v4-flash", "deepseek"),
    ("dashscope/qwen-max", "dashscope"),
    ("dashscope/kimi-k2.6", "dashscope"),
    ("dashscope/glm-5.1", "dashscope"),
    ("wyzlab/gpt-5.5", "wyzlab"),
    ("wyzlab/grok-4", "wyzlab"),
]

BD_MODELS = [
    ("deepseek/deepseek-v4-flash", "deepseek"),
    ("dashscope/qwen-max", "dashscope"),
    ("wyzlab/gpt-5.5", "wyzlab"),
    ("wyzlab/grok-4", "wyzlab"),
]

ENV_TASKS = {
    "retail": list(range(20)),
    "airline": list(range(50)),
}
SEEDS = [0, 1, 2]

BD_MUTATIONS = [
    "B1_type_change",
    "B2_requiredness_change",
    "B3_enum_change",
    "B4_output_schema_change",
    "D1_error_format_change",
    "D2_permission_change",
    "D3_pagination_change",
    "D4_rate_limit_change",
]
BD_PROTOCOLS = ["used_tool", "unused_tool", "intent_aligned", "random"]

MAX_NUM_STEPS = 30
TIMEOUT_SECONDS = 600


def _short_model(model: str) -> str:
    return model.split("/", 1)[-1]


def _mutation_class(mutation: str | None) -> str | None:
    if not mutation:
        return None
    return mutation[0] if mutation[0] in {"A", "B", "C", "D"} else "unknown"


def _stable_key(parts: list[Any]) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"p5_{digest}"


def _cell(
    *,
    experiment: str,
    env: str,
    model: str,
    provider: str,
    task_id: int,
    seed: int,
    condition: str,
    mutation_name: str | None,
    observability_level: str | None,
    protocol: str | None,
    requires_baseline_success: bool,
    stage: str,
    execution_mode: str = "live",
    baseline_success: bool | None = None,
    baseline_reward: float | None = None,
) -> dict[str, Any]:
    mutation_class = _mutation_class(mutation_name)
    cell_key = _stable_key(
        [
            experiment,
            env,
            model,
            task_id,
            seed,
            condition,
            mutation_name,
            observability_level,
            protocol,
            stage,
        ]
    )
    return {
        "phase": "phase5",
        "stage": stage,
        "experiment": experiment,
        "env": env,
        "model": model,
        "provider": provider,
        "task_id": task_id,
        "seed": seed,
        "condition": condition,
        "mutation_class": mutation_class,
        "mutation_name": mutation_name,
        "observability_level": observability_level,
        "protocol": protocol or "none",
        "target_tool": None,
        "requires_baseline_success": requires_baseline_success,
        "baseline_success": baseline_success,
        "baseline_reward": baseline_reward,
        "max_num_steps": MAX_NUM_STEPS,
        "timeout_seconds": TIMEOUT_SECONDS,
        "execution_mode": execution_mode,
        "cell_key": cell_key,
    }


def baseline_cells() -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for env, tasks in ENV_TASKS.items():
        for model, provider in MAIN_MODELS:
            for task_id in tasks:
                for seed in SEEDS:
                    cells.append(
                        _cell(
                            experiment="baseline_selection",
                            env=env,
                            model=model,
                            provider=provider,
                            task_id=task_id,
                            seed=seed,
                            condition="baseline",
                            mutation_name=None,
                            observability_level=None,
                            protocol=None,
                            requires_baseline_success=False,
                            stage="baseline",
                        )
                    )
    return cells


def candidate_mutation_cells() -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for env, tasks in ENV_TASKS.items():
        for model, provider in MAIN_MODELS:
            for task_id in tasks:
                for seed in SEEDS:
                    for level in OBSERVABILITY_LEVELS:
                        cells.append(
                            _cell(
                                experiment="observability_gradient",
                                env=env,
                                model=model,
                                provider=provider,
                                task_id=task_id,
                                seed=seed,
                                condition=level,
                                mutation_name="C4_business_rule_drift",
                                observability_level=level,
                                protocol="intent_aligned",
                                requires_baseline_success=True,
                                stage="mutation_candidate",
                            )
                        )
                    if (model, provider) in BD_MODELS:
                        for mutation in BD_MUTATIONS:
                            for protocol in BD_PROTOCOLS:
                                cells.append(
                                    _cell(
                                        experiment="B_D_mutations",
                                        env=env,
                                        model=model,
                                        provider=provider,
                                        task_id=task_id,
                                        seed=seed,
                                        condition=mutation,
                                        mutation_name=mutation,
                                        observability_level=None,
                                        protocol=protocol,
                                        requires_baseline_success=True,
                                        stage="mutation_candidate",
                                    )
                                )
    return cells


def smoke_cells(execution_mode: str = "local_fake") -> list[dict[str, Any]]:
    base = {
        "env": "retail",
        "model": "deepseek/deepseek-v4-flash",
        "provider": "deepseek",
        "task_id": 0,
        "seed": 0,
        "execution_mode": execution_mode,
    }
    return [
        _cell(
            experiment="smoke",
            condition="baseline",
            mutation_name=None,
            observability_level=None,
            protocol=None,
            requires_baseline_success=False,
            stage="smoke",
            baseline_success=None,
            **base,
        ),
        _cell(
            experiment="smoke",
            condition="O0_silent",
            mutation_name="C4_business_rule_drift",
            observability_level="O0_silent",
            protocol="intent_aligned",
            requires_baseline_success=True,
            stage="smoke",
            baseline_success=True,
            baseline_reward=1.0,
            **base,
        ),
        _cell(
            experiment="smoke",
            condition="O2_policy_error",
            mutation_name="C4_business_rule_drift",
            observability_level="O2_policy_error",
            protocol="intent_aligned",
            requires_baseline_success=True,
            stage="smoke",
            baseline_success=True,
            baseline_reward=1.0,
            **base,
        ),
        _cell(
            experiment="smoke",
            condition="O4_migration_note",
            mutation_name="C4_business_rule_drift",
            observability_level="O4_migration_note",
            protocol="intent_aligned",
            requires_baseline_success=True,
            stage="smoke",
            baseline_success=True,
            baseline_reward=1.0,
            **base,
        ),
    ]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        print(f"[warn] missing baseline results: {path}")
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"[warn] {path}:{line_no}: {exc}")
    return rows


def _is_success(row: dict[str, Any]) -> bool:
    reward = row.get("final_reward", row.get("reward"))
    try:
        return float(reward or 0) > 0
    except Exception:
        return False


def _baseline_status_label(success_count: int) -> str:
    if success_count >= 20:
        return "main_ready"
    if success_count >= 15:
        return "usable"
    if success_count >= 5:
        return "exploratory"
    return "insufficient"


def _read_baseline_latest(paths: list[Path]) -> dict[tuple[Any, ...], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(_read_jsonl(path))
    latest: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        if row.get("fake_run"):
            continue
        if row.get("condition") != "baseline":
            continue
        if row.get("status") != "ok":
            continue
        key = (row.get("env"), row.get("model"), int(row.get("task_id", row.get("task_index", 0))), int(row.get("seed", 0)))
        latest[key] = row
    return latest


def _baseline_group_status(latest: dict[tuple[Any, ...], dict[str, Any]]) -> dict[tuple[str, str, str], str]:
    counts: dict[tuple[str, str, str], int] = collections.Counter()
    for (_env, _model, _task, _seed), row in latest.items():
        if _is_success(row):
            provider = str(row.get("provider") or str(_model).split("/", 1)[0])
            counts[(str(_env), str(_model), provider)] += 1
    return {key: _baseline_status_label(count) for key, count in counts.items()}


def mutation_cells_from_baselines(paths: list[Path]) -> list[dict[str, Any]]:
    latest = _read_baseline_latest(paths)

    cells: list[dict[str, Any]] = []
    for (env, model, task_id, seed), row in sorted(latest.items()):
        if not _is_success(row):
            continue
        provider = str(row.get("provider") or model.split("/", 1)[0])
        reward = float(row.get("final_reward", row.get("reward", 1.0)) or 1.0)
        for level in OBSERVABILITY_LEVELS:
            cells.append(
                _cell(
                    experiment="observability_gradient",
                    env=str(env),
                    model=str(model),
                    provider=provider,
                    task_id=task_id,
                    seed=seed,
                    condition=level,
                    mutation_name="C4_business_rule_drift",
                    observability_level=level,
                    protocol="intent_aligned",
                    requires_baseline_success=True,
                    stage="mutation_from_baseline",
                    baseline_success=True,
                    baseline_reward=reward,
                )
            )
        if str(model) in {m for m, _ in BD_MODELS}:
            for mutation in BD_MUTATIONS:
                for protocol in BD_PROTOCOLS:
                    cells.append(
                        _cell(
                            experiment="B_D_mutations",
                            env=str(env),
                            model=str(model),
                            provider=provider,
                            task_id=task_id,
                            seed=seed,
                            condition=mutation,
                            mutation_name=mutation,
                            observability_level=None,
                            protocol=protocol,
                            requires_baseline_success=True,
                            stage="mutation_from_baseline",
                            baseline_success=True,
                            baseline_reward=reward,
                        )
                    )
    return cells


def _norm_experiment(value: str) -> str:
    low = value.lower()
    if low in {"observability", "observability_gradient", "c4"}:
        return "observability_gradient"
    if low in {"bd", "b_d", "b_d_mutations", "bd_mutations"}:
        return "B_D_mutations"
    return value


def _model_matches(model: str, allowed: list[str] | None) -> bool:
    if not allowed:
        return True
    short = _short_model(model)
    candidates = {model, short, model.lower(), short.lower()}
    return any(a in candidates or a.lower() in candidates for a in allowed)


def _apply_filters(
    cells: list[dict[str, Any]],
    *,
    only_experiment: list[str] | None = None,
    only_env: list[str] | None = None,
    only_model: list[str] | None = None,
    exclude_provider: list[str] | None = None,
    only_mutation_class: list[str] | None = None,
    only_observability_level: list[str] | None = None,
    max_cells_per_env_model: int | None = None,
    exclude_status: list[str] | None = None,
    baseline_status: dict[tuple[str, str, str], str] | None = None,
) -> list[dict[str, Any]]:
    experiments = {_norm_experiment(x) for x in only_experiment or []}
    envs = {x.lower() for x in only_env or []}
    excluded_providers = {x.lower() for x in exclude_provider or []}
    classes = {x.upper() for x in only_mutation_class or []}
    levels = set(only_observability_level or [])
    excluded = {x.lower() for x in exclude_status or []}
    out: list[dict[str, Any]] = []
    for cell in cells:
        if experiments and cell.get("experiment") not in experiments:
            continue
        if envs and str(cell.get("env", "")).lower() not in envs:
            continue
        if excluded_providers and str(cell.get("provider", "")).lower() in excluded_providers:
            continue
        if not _model_matches(str(cell.get("model", "")), only_model):
            continue
        if classes and str(cell.get("mutation_class") or "").upper() not in classes:
            continue
        if levels and cell.get("observability_level") not in levels:
            continue
        if excluded and baseline_status is not None:
            key = (str(cell.get("env")), str(cell.get("model")), str(cell.get("provider")))
            status = baseline_status.get(key, "insufficient").lower()
            if status in excluded:
                continue
        out.append(cell)
    if max_cells_per_env_model is not None and max_cells_per_env_model > 0:
        limited: list[dict[str, Any]] = []
        counts: dict[tuple[str, str], int] = collections.Counter()
        for cell in sorted(out, key=lambda c: (c.get("env"), c.get("model"), c.get("task_id"), c.get("seed"), c.get("experiment"), c.get("condition"), c.get("protocol"))):
            key = (str(cell.get("env")), str(cell.get("model")))
            if counts[key] >= max_cells_per_env_model:
                continue
            counts[key] += 1
            limited.append(cell)
        out = limited
    return out


def summarize(cells: list[dict[str, Any]]) -> dict[str, Any]:
    by_stage = collections.Counter(str(c["stage"]) for c in cells)
    by_experiment = collections.Counter(str(c["experiment"]) for c in cells)
    by_provider = collections.Counter(str(c["provider"]) for c in cells)
    by_env_model_provider = collections.Counter(
        f"{c['env']}|{_short_model(c['model'])}|{c['provider']}" for c in cells
    )
    baseline_n = sum(1 for c in cells if c["condition"] == "baseline")
    mutation_n = len(cells) - baseline_n
    provider_calls = dict(sorted(by_provider.items()))
    return {
        "total_cells": len(cells),
        "baseline_stage_cells": baseline_n,
        "mutation_stage_candidate_cells": mutation_n,
        "estimated_api_calls": len([c for c in cells if c.get("execution_mode") == "live"]),
        "estimated_max_runtime_hours_serial": round(
            sum(int(c.get("timeout_seconds", TIMEOUT_SECONDS)) for c in cells if c.get("execution_mode") == "live") / 3600,
            2,
        ),
        "counts_by_stage": dict(sorted(by_stage.items())),
        "counts_by_experiment": dict(sorted(by_experiment.items())),
        "counts_by_provider": provider_calls,
        "counts_by_env_model_provider": dict(sorted(by_env_model_provider.items())),
        "models": [_short_model(m) for m, _ in MAIN_MODELS],
        "bd_models": [_short_model(m) for m, _ in BD_MODELS],
        "observability_levels": OBSERVABILITY_LEVELS,
        "bd_mutations": BD_MUTATIONS,
        "bd_protocols": BD_PROTOCOLS,
        "two_stage_supported": True,
        "mutation_generation_command": (
            "python code/schema_mutation/phase5_plan.py --from-baseline-glob "
            "\"runs/schema_mutation/phase5/status/baseline_*_status.jsonl\" --write-shards"
        ),
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_shards(cells: list[dict[str, Any]], shard_size: int, shard_prefix: str | None = None) -> list[Path]:
    SHARDS.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    if shard_prefix is not None:
        for idx in range(math.ceil(len(cells) / shard_size) or 1):
            chunk = cells[idx * shard_size : (idx + 1) * shard_size]
            if not chunk:
                continue
            path = SHARDS / f"{shard_prefix}_{idx:04d}.jsonl"
            write_jsonl(path, chunk)
            paths.append(path)
        return paths

    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for cell in cells:
        grouped[str(cell.get("stage", "unknown"))].append(cell)

    for stage, stage_cells in sorted(grouped.items()):
        for idx in range(math.ceil(len(stage_cells) / shard_size) or 1):
            chunk = stage_cells[idx * shard_size : (idx + 1) * shard_size]
            if not chunk:
                continue
            path = SHARDS / f"{stage}_{idx:04d}.jsonl"
            write_jsonl(path, chunk)
            paths.append(path)

    smoke_path = SHARDS / "smoke.jsonl"
    write_jsonl(smoke_path, smoke_cells("local_fake"))
    paths.append(smoke_path)
    live_smoke_path = SHARDS / "smoke_live.jsonl"
    write_jsonl(live_smoke_path, smoke_cells("live"))
    paths.append(live_smoke_path)
    return paths


def _filtered_shard_prefix(from_baseline: bool, only_experiment: list[str] | None) -> str | None:
    if not from_baseline:
        return None
    experiments = {_norm_experiment(x) for x in only_experiment or []}
    if experiments == {"observability_gradient"}:
        return "observability_from_baseline"
    if experiments == {"B_D_mutations"}:
        return "bd_from_baseline"
    return "mutation_from_baseline"


def write_plan_artifacts(cells: list[dict[str, Any]], summary: dict[str, Any], shard_paths: list[Path]) -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": summary,
        "shards": [str(p.relative_to(_REPO_ROOT)) for p in shard_paths],
        "cells": cells,
    }
    (RUNS / "phase5_plan.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Phase 5 Large-Scale Experiment Plan",
        "",
        "This plan separates baseline selection from mutation execution. Mutation cells are candidates until baseline success is observed.",
        "",
        f"- total cells: {summary['total_cells']}",
        f"- baseline stage cells: {summary['baseline_stage_cells']}",
        f"- mutation-stage candidate cells: {summary['mutation_stage_candidate_cells']}",
        f"- estimated API calls: {summary['estimated_api_calls']}",
        f"- estimated serial timeout upper bound: {summary['estimated_max_runtime_hours_serial']} hours",
        f"- two-stage planning supported: {summary['two_stage_supported']}",
        "",
        "## Counts By Provider",
    ]
    lines.extend(f"- {k}: {v}" for k, v in summary["counts_by_provider"].items())
    lines.extend(["", "## Counts By Env / Model / Provider"])
    lines.extend(f"- {k}: {v}" for k, v in summary["counts_by_env_model_provider"].items())
    lines.extend(["", "## Shards"])
    lines.extend(f"- `{p.relative_to(_REPO_ROOT)}`" for p in shard_paths)
    (RUNS / "phase5_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write-shards", action="store_true")
    parser.add_argument("--shard-size", type=int, default=100)
    parser.add_argument("--shard-prefix", default=None, help="Custom prefix for written shard files.")
    parser.add_argument("--baseline-only", action="store_true", help="Alias for --stage baseline.")
    parser.add_argument(
        "--stage",
        choices=["full", "baseline", "candidate-mutations"],
        default="full",
        help="Select candidate plan stage. Ignored when --from-baseline-results is used.",
    )
    parser.add_argument(
        "--from-baseline-results",
        nargs="*",
        default=None,
        help="Status/raw JSONL files from baseline shards; generate mutation cells for successful baselines only.",
    )
    parser.add_argument(
        "--from-baseline-glob",
        default=None,
        help="Glob for baseline status/raw JSONL files; useful on Windows where shell glob expansion is not automatic.",
    )
    parser.add_argument("--only-experiment", action="append", choices=["observability_gradient", "bd_mutations", "B_D_mutations"], default=None)
    parser.add_argument("--only-env", action="append", choices=["retail", "airline"], default=None)
    parser.add_argument("--only-model", action="append", default=None)
    parser.add_argument("--exclude-provider", action="append", default=None)
    parser.add_argument("--only-mutation-class", action="append", choices=["B", "D", "b", "d"], default=None)
    parser.add_argument("--only-observability-level", action="append", choices=OBSERVABILITY_LEVELS, default=None)
    parser.add_argument("--max-cells-per-env-model", type=int, default=None)
    parser.add_argument(
        "--exclude-status",
        action="append",
        choices=["main_ready", "usable", "exploratory", "insufficient"],
        default=None,
        help="Exclude env/model/provider baseline groups with this audit status.",
    )
    args = parser.parse_args()

    from_baseline = False
    baseline_status: dict[tuple[str, str, str], str] | None = None
    if args.baseline_only:
        args.stage = "baseline"

    if args.from_baseline_glob:
        from_baseline = True
        pattern = Path(args.from_baseline_glob)
        if pattern.is_absolute():
            paths = sorted(pattern.parent.glob(pattern.name))
        else:
            paths = sorted(_REPO_ROOT.glob(str(pattern).replace("\\", "/")))
        latest = _read_baseline_latest(paths)
        baseline_status = _baseline_group_status(latest)
        cells = mutation_cells_from_baselines(paths)
    elif args.from_baseline_results is not None:
        from_baseline = True
        paths = [Path(p) if Path(p).is_absolute() else _REPO_ROOT / p for p in args.from_baseline_results]
        latest = _read_baseline_latest(paths)
        baseline_status = _baseline_group_status(latest)
        cells = mutation_cells_from_baselines(paths)
    elif args.stage == "baseline":
        cells = baseline_cells()
    elif args.stage == "candidate-mutations":
        cells = candidate_mutation_cells()
    else:
        cells = baseline_cells() + candidate_mutation_cells()

    cells = _apply_filters(
        cells,
        only_experiment=args.only_experiment,
        only_env=args.only_env,
        only_model=args.only_model,
        exclude_provider=args.exclude_provider,
        only_mutation_class=args.only_mutation_class,
        only_observability_level=args.only_observability_level,
        max_cells_per_env_model=args.max_cells_per_env_model,
        exclude_status=args.exclude_status,
        baseline_status=baseline_status,
    )

    summary = summarize(cells)
    if from_baseline and not cells:
        print("[warn] no mutation cells selected from baseline results; run baseline shards or relax filters")
    if from_baseline and baseline_status:
        print("[baseline_status]")
        for key, status in sorted(baseline_status.items()):
            print(f"  {key[0]} | {key[1]} | {key[2]} -> {status}")
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))
    if args.dry_run:
        print("\n[dry-run] first planned cells:")
        for cell in cells[:10]:
            print(json.dumps(cell, ensure_ascii=False, sort_keys=True))
        print(f"[dry-run] planned_cells={len(cells)}")
        return 0

    shard_paths: list[Path] = []
    if args.write_shards:
        shard_prefix = args.shard_prefix or _filtered_shard_prefix(from_baseline, args.only_experiment)
        shard_paths = write_shards(
            cells,
            max(1, args.shard_size),
            shard_prefix=shard_prefix,
        )
    write_plan_artifacts(cells, summary, shard_paths)
    print(f"plan_json={RUNS / 'phase5_plan.json'}")
    print(f"plan_md={RUNS / 'phase5_plan.md'}")
    if shard_paths:
        print(f"shard_count={len(shard_paths)}")
        print(f"smoke_shard={SHARDS / 'smoke.jsonl'}")
        print(f"live_smoke_shard={SHARDS / 'smoke_live.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
