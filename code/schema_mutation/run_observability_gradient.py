"""Phase 1 runner for the C4 observability-gradient experiment.

This is a thin orchestration layer around ``batch_runner.run_batch``. It exists
so the O0-O4 matrix is explicit and dry-runnable without hand-writing five
separate commands.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from code.schema_mutation.batch_runner import run_batch  # noqa: E402
from code.schema_mutation.c4_observability_modes import (  # noqa: E402
    OBSERVABILITY_LEVELS,
    runtime_mode_for_level,
)


MODEL_PRESETS = {
    "retail_main": [
        "deepseek/deepseek-v4-flash",
        "dashscope/qwen-max",
        "dashscope/kimi-k2.6",
        "wyzlab/gpt-5.5",
        "wyzlab/grok-4",
        "dashscope/glm-5.1",
    ],
    "airline_expanded": [
        "deepseek/deepseek-v4-flash",
        "dashscope/qwen-max",
        "wyzlab/gpt-5.5",
        "wyzlab/grok-4",
    ],
}


def _parse_ints(spec: str) -> list[int]:
    """Parse ``0,1,2`` plus ranges such as ``0-19``."""
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            step = 1 if end >= start else -1
            out.extend(range(start, end + step, step))
        else:
            out.append(int(part))
    return out


def _parse_csv(spec: str) -> list[str]:
    return [x.strip() for x in spec.split(",") if x.strip()]


def _default_models(env_name: str) -> list[str]:
    return MODEL_PRESETS["airline_expanded" if env_name == "airline" else "retail_main"]


def _existing_baseline_good_tasks(env_name: str) -> list[int]:
    tasks: set[int] = set()
    runs_dir = _REPO_ROOT / "runs" / "schema_mutation"
    for path in sorted(runs_dir.glob("*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("env", "retail") != env_name:
                continue
            if row.get("fake_run"):
                continue
            if row.get("status") != "ok" or row.get("mutation_type") is not None:
                continue
            if float(row.get("reward") or row.get("final_reward") or 0.0) > 0:
                try:
                    tasks.add(int(row["task_index"]))
                except Exception:
                    pass
    return sorted(tasks)


def _write_fake_run(
    *,
    out_path: Path,
    env_name: str,
    tasks: list[int],
    models: list[str],
    seeds: list[int],
) -> None:
    """Write a tiny marked fake run for summary smoke tests.

    These rows are never meant to be reported as results. They are explicitly
    flagged with ``fake_run=true`` and only exercise the JSONL/summary plumbing.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for task in tasks[:2]:
        for model in models[:2]:
            for seed in seeds[:1]:
                rows.append(
                    {
                        "fake_run": True,
                        "env": env_name,
                        "task_index": task,
                        "model": model,
                        "mutation_type": None,
                        "seed": seed,
                        "target_policy": "intent_aligned",
                        "c4_runtime_mode": None,
                        "observability_level": None,
                        "status": "ok",
                        "reward": 1.0,
                        "final_reward": 1.0,
                        "num_actions": 3,
                        "mutation_applied": False,
                        "mutation_tool": None,
                        "target_tool": None,
                        "intent_aligned": False,
                        "failure_mode": "agent_compatible",
                        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    }
                )
                for i, level in enumerate(OBSERVABILITY_LEVELS):
                    success = 1.0 if i >= 3 else 0.0
                    violation = success <= 0.0
                    rows.append(
                        {
                            "fake_run": True,
                            "env": env_name,
                            "task_index": task,
                            "model": model,
                            "mutation_type": "C4_business_rule_drift",
                            "seed": seed,
                            "target_policy": "intent_aligned",
                            "c4_runtime_mode": runtime_mode_for_level(level),
                            "observability_level": level,
                            "status": "ok",
                            "reward": success,
                            "final_reward": success,
                            "num_actions": 4 + i,
                            "mutation_applied": True,
                            "mutation_tool": "fake_target_tool",
                            "target_tool": "fake_target_tool",
                            "intent_aligned": True,
                            "oracle_rule_violation": violation,
                            "visible_policy_error": violation and i > 0,
                            "generic_error_visible": violation and level == "O1_generic_error",
                            "structured_policy_error_visible": violation
                            and level in {"O3_structured_policy_error", "O4_migration_note"},
                            "migration_note_visible": level == "O4_migration_note",
                            "hidden_business_rule_violation": violation and level == "O0_silent",
                            "recovery_attempted": violation and i > 0,
                            "recovery_success": False,
                            "failure_mode": "agent_compatible" if success else "smoke_failure",
                            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        }
                    )
    with out_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[fake-run] wrote rows={len(rows)} out={out_path}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--env", default="retail", choices=["retail", "airline"])
    p.add_argument("--tasks", default=None, help="comma list or range, e.g. 0,1,4 or 0-19")
    p.add_argument("--models", default=None, help="comma-separated model ids; defaults depend on env")
    p.add_argument("--seeds", default="0,1,2")
    p.add_argument("--out", default=None)
    p.add_argument("--env-user-model", default=None)
    p.add_argument("--env-user-provider", default=None)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument(
        "--target-policy",
        default="intent_aligned",
        choices=["intent_aligned", "random_intent_aligned", "used_tool", "random"],
    )
    p.add_argument("--max-num-steps", type=int, default=30)
    p.add_argument("--cell-timeout-seconds", type=int, default=240)
    p.add_argument("--skip-existing-ok", action="store_true")
    p.add_argument("--keep-going-on-quota", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--fake-run", action="store_true", help="write marked fake rows for smoke-testing summaries")
    args = p.parse_args()

    if args.tasks:
        tasks = _parse_ints(args.tasks)
    else:
        tasks = _existing_baseline_good_tasks(args.env)
        if not tasks:
            tasks = _parse_ints("0-19" if args.env == "airline" else "0-9")
    models = _parse_csv(args.models) if args.models else _default_models(args.env)
    seeds = _parse_ints(args.seeds)

    out_path = Path(
        args.out
        or f"runs/schema_mutation/observability_gradient_{args.env}.jsonl"
    )
    if not out_path.is_absolute():
        out_path = _REPO_ROOT / out_path

    if args.fake_run:
        _write_fake_run(out_path=out_path, env_name=args.env, tasks=tasks, models=models, seeds=seeds)
        return 0

    env_user_model = args.env_user_model or "dashscope/qwen-flash"
    env_user_provider = args.env_user_provider or "dashscope"

    print("[gradient] Phase 1 C4 observability gradient")
    print(f"[gradient] env={args.env} tasks={tasks} seeds={seeds}")
    print(f"[gradient] models={models}")
    print(f"[gradient] out={out_path}")
    print(f"[gradient] dry_run={args.dry_run}")

    rc = run_batch(
        tasks=tasks,
        models=models,
        mutations=[None],
        seeds=seeds,
        out_path=out_path,
        env_user_model=env_user_model,
        env_user_provider=env_user_provider,
        temperature=args.temperature,
        stop_on_quota=not args.keep_going_on_quota,
        skip_existing_ok=args.skip_existing_ok,
        exposure_map=None,
        target_policy=args.target_policy,
        c4_runtime_mode="visible",
        observability_level=None,
        env_name=args.env,
        max_num_steps=args.max_num_steps,
        cell_timeout_seconds=args.cell_timeout_seconds,
        dry_run=args.dry_run,
    )
    if rc not in {0, 1}:
        return rc

    for level in OBSERVABILITY_LEVELS:
        rc = run_batch(
            tasks=tasks,
            models=models,
            mutations=["C4_business_rule_drift"],
            seeds=seeds,
            out_path=out_path,
            env_user_model=env_user_model,
            env_user_provider=env_user_provider,
            temperature=args.temperature,
            stop_on_quota=not args.keep_going_on_quota,
            skip_existing_ok=args.skip_existing_ok,
            exposure_map=None,
            target_policy=args.target_policy,
            c4_runtime_mode=runtime_mode_for_level(level),
            observability_level=level,
            env_name=args.env,
            max_num_steps=args.max_num_steps,
            cell_timeout_seconds=args.cell_timeout_seconds,
            dry_run=args.dry_run,
        )
        if rc not in {0, 1}:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
