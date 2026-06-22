"""Batch runner for schema-mutation τ-bench pilots.

This bypasses HAL's `hal-eval` CLI because HAL currently forces W&B Weave
login. It still uses the same τ-bench environment and `runner.run()` agent
function, so the experimental runtime is identical to our Day-3 smoke tests.

Example:
    python -m code.schema_mutation.batch_runner \
      --tasks 0,1 \
      --models dashscope/qwen3.7-max-2026-06-08,dashscope/qwen-flash \
      --mutations baseline,A1_identifier_rename,C1_unit_scale_drift \
      --seeds 0 \
      --out runs/schema_mutation/day4_smoke.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_REPO_ROOT / ".env")
except Exception:
    pass

from code.schema_mutation.runner import run as run_one  # noqa: E402
from code.schema_mutation.c4_observability_modes import (  # noqa: E402
    OBSERVABILITY_LEVELS,
    normalize_observability_level,
    runtime_mode_for_level,
)


DEFAULT_CFG = {
    "env": "retail",
    "user_strategy": "llm",
    "user_model": "dashscope/qwen-flash",
    "task_split": "test",
    "user_provider": "dashscope",
}

QUOTA_PATTERNS = [
    "quota", "insufficient_quota", "insufficient quota", "balance", "余额",
    "欠费", "prepaid", "free tier", "free quota", "no credits",
    "billing", "credit", "account_debt", "overdue-payment", "overdue",
    "access denied", "good standing", "account is in good standing",
]


def _is_quota_error(text: str) -> bool:
    low = text.lower()
    return any(p in low for p in QUOTA_PATTERNS)


def _parse_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def _make_input(task_index: int, env_name: str = "retail") -> dict[str, dict[str, Any]]:
    cfg = dict(DEFAULT_CFG)
    cfg["env"] = env_name
    cfg["task_index"] = task_index
    return {str(task_index): cfg}


def _run_one_isolated(
    task_index: int,
    env_name: str,
    run_kwargs: dict[str, Any],
    timeout_s: int,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="schema_mut_cell_") as tmp:
        tmp_dir = Path(tmp)
        payload_path = tmp_dir / "payload.json"
        result_path = tmp_dir / "result.json"
        payload_path.write_text(
            json.dumps(
                {"task_index": task_index, "env": env_name, "run_kwargs": run_kwargs},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        cmd = [
            sys.executable,
            "-m",
            "code.schema_mutation.single_cell_runner",
            str(payload_path),
            str(result_path),
        ]
        proc = subprocess.Popen(
            cmd,
            cwd=str(_REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired as e:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                proc.kill()
            proc.communicate()
            raise TimeoutError(f"cell timeout after {timeout_s}s") from e
        if proc.returncode != 0:
            msg = (stderr or stdout or "").strip()
            raise RuntimeError(msg[:4000] or f"cell subprocess failed: {proc.returncode}")

        return json.loads(result_path.read_text(encoding="utf-8"))


def _summarize(record: dict[str, Any]) -> str:

    if record["status"] != "ok":
        return f"ERROR {record.get('error_type')}: {record.get('error', '')[:120]}"
    return (
        f"reward={record['reward']} actions={record['num_actions']} "
        f"obs={record.get('observability_level')} "
        f"applied={record.get('mutation_applied')} "
        f"tool={record.get('mutation_tool')} note={str(record.get('mutation_note'))[:70]}"
    )


def _cell_key(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("env", "retail"),
        record.get("task_index"),
        record.get("model"),
        record.get("mutation_type"),
        record.get("seed"),
        record.get("env_user_model"),
        record.get("env_user_provider"),
        record.get("temperature"),
        record.get("target_policy", "random"),
        record.get("c4_runtime_mode", "visible"),
        record.get("observability_level"),
        record.get("max_num_steps", 30),

    )


def _load_existing_ok(out_path: Path) -> set[tuple[Any, ...]]:
    """Return cell keys that already have at least one OK record."""
    keys: set[tuple[Any, ...]] = set()
    if not out_path.exists():
        return keys
    with out_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("status") == "ok":
                keys.add(_cell_key(r))
    return keys


def run_batch(
    tasks: list[int],
    models: list[str],
    mutations: list[str | None],
    seeds: list[int],
    out_path: Path,
    env_user_model: str,
    env_user_provider: str,
    temperature: float,
    stop_on_quota: bool = True,
    skip_existing_ok: bool = False,
    exposure_map: dict[str, Any] | None = None,
    target_policy: str = "random",
    c4_runtime_mode: str = "visible",
    observability_level: str | None = None,
    env_name: str = "retail",
    max_num_steps: int = 30,
    cell_timeout_seconds: int = 0,
    target_tools: list[str] | None = None,
    avoid_tools: list[str] | None = None,
    business_rule_intent: str | None = None,
    business_rule_drift: str | None = None,
    dry_run: bool = False,
) -> int:




    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = len(tasks) * len(models) * len(mutations) * len(seeds)
    done = 0
    skipped = 0
    ok = 0
    failed = 0
    quota_hit = False
    existing_ok = _load_existing_ok(out_path) if skip_existing_ok else set()

    print(f"[batch] total={total} out={out_path}", flush=True)
    print(f"[batch] env={env_name}", flush=True)
    print(f"[batch] tasks={tasks}", flush=True)

    print(f"[batch] models={models}", flush=True)
    print(f"[batch] mutations={[m or 'baseline' for m in mutations]}", flush=True)
    print(f"[batch] seeds={seeds}", flush=True)
    print(f"[batch] target_policy={target_policy}", flush=True)
    normalized_observability_level = normalize_observability_level(
        observability_level, c4_runtime_mode
    )
    if observability_level:
        c4_runtime_mode = runtime_mode_for_level(normalized_observability_level)

    print(f"[batch] c4_runtime_mode={c4_runtime_mode}", flush=True)
    print(f"[batch] observability_level={normalized_observability_level}", flush=True)
    print(f"[batch] max_num_steps={max_num_steps}", flush=True)
    print(f"[batch] cell_timeout_seconds={cell_timeout_seconds}", flush=True)
    print(f"[batch] dry_run={dry_run}", flush=True)

    if skip_existing_ok:


        print(f"[batch] skip_existing_ok=True ({len(existing_ok)} completed cells found)", flush=True)
    if exposure_map is not None:
        print(f"[batch] exposure_map tasks={len(exposure_map)}", flush=True)
    print("", flush=True)

    if dry_run:
        for task_index in tasks:
            for model in models:
                for mutation in mutations:
                    for seed in seeds:
                        print(
                            "PLAN "
                            f"env={env_name} task={task_index} model={model} "
                            f"mutation={mutation or 'baseline'} seed={seed} "
                            f"target_policy={target_policy} "
                            f"observability_level={normalized_observability_level} "
                            f"c4_runtime_mode={c4_runtime_mode}",
                            flush=True,
                        )
        print(f"\n[dry-run] planned_cells={total} out={out_path}", flush=True)
        return 0

    with out_path.open("a", encoding="utf-8") as f:
        for task_index in tasks:
            for model in models:
                for mutation in mutations:
                    for seed in seeds:
                        done += 1
                        tag = mutation or "baseline"
                        record: dict[str, Any] = {
                            "env": env_name,
                            "task_index": task_index,
                            "model": model,

                            "mutation_type": mutation,
                            "seed": seed,
                            "env_user_model": env_user_model,
                            "env_user_provider": env_user_provider,
                            "temperature": temperature,
                            "target_policy": target_policy,
                            "c4_runtime_mode": c4_runtime_mode,
                            "observability_level": normalized_observability_level,
                            "max_num_steps": max_num_steps,
                            "cell_timeout_seconds": cell_timeout_seconds,
                            "status": "pending",
                            "target_tool": None,
                            "intent_aligned": False,
                            "visible_policy_error": False,
                            "generic_error_visible": False,
                            "structured_policy_error_visible": False,
                            "migration_note_visible": normalized_observability_level == "O4_migration_note",
                            "oracle_rule_violation": False,
                            "hidden_business_rule_violation": False,
                            "recovery_attempted": False,
                            "recovery_success": False,
                            "final_reward": None,
                            "failure_mode": None,


                            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        }
                        if skip_existing_ok and _cell_key(record) in existing_ok:
                            skipped += 1
                            print(
                                f"[{done:03d}/{total}] SKIP existing ok: "
                                f"task={task_index} model={model} mutation={tag} seed={seed}",
                                flush=True,
                            )
                            continue

                        t0 = time.time()
                        print(
                            f"[{done:03d}/{total}] task={task_index} model={model} "
                            f"mutation={tag} seed={seed} ...",
                            flush=True,
                        )
                        try:
                            run_kwargs: dict[str, Any] = {
                                "agent_model_name": model,
                                "mutation_type": mutation,
                                "seed": seed,
                                "temperature": temperature,
                                "env_user_model": env_user_model,
                                "env_user_provider": env_user_provider,
                                "c4_runtime_mode": c4_runtime_mode,
                                "observability_level": normalized_observability_level,
                                "target_policy": target_policy,
                                "max_num_steps": max_num_steps,
                            }


                            if mutation and target_policy != "random":
                                exp = exposure_map.get(str(task_index), {}) if exposure_map is not None else {}
                                used_tools = exp.get("used_tools", []) or []
                                if target_policy == "used_tool":
                                    run_kwargs["target_tools"] = ",".join(used_tools)
                                    record["target_tools"] = used_tools
                                elif target_policy == "unused_tool":
                                    run_kwargs["avoid_tools"] = ",".join(used_tools)
                                    record["avoid_tools"] = used_tools
                                elif target_policy == "intent_aligned":
                                    run_kwargs["target_tools"] = ",".join(used_tools)
                                    run_kwargs["intent_aligned"] = "true"
                                    record["target_tools"] = used_tools
                                    record["intent_aligned"] = True
                                elif target_policy == "unused_intent_aligned":
                                    run_kwargs["avoid_tools"] = ",".join(used_tools)
                                    run_kwargs["intent_aligned"] = "true"
                                    record["avoid_tools"] = used_tools
                                    record["intent_aligned"] = True
                                elif target_policy == "random_intent_aligned":
                                    run_kwargs["intent_aligned"] = "true"
                                    record["intent_aligned"] = True
                                else:
                                    raise ValueError(f"unknown target_policy: {target_policy}")

                            if mutation and target_tools:
                                run_kwargs["target_tools"] = ",".join(target_tools)
                                record["target_tools"] = target_tools
                            if mutation and avoid_tools:
                                run_kwargs["avoid_tools"] = ",".join(avoid_tools)
                                record["avoid_tools"] = avoid_tools
                            if mutation and business_rule_intent:
                                run_kwargs["business_rule_intent"] = business_rule_intent
                                record["business_rule_intent"] = business_rule_intent
                            if mutation and business_rule_drift:
                                run_kwargs["business_rule_drift"] = business_rule_drift
                                record["business_rule_drift"] = business_rule_drift

                            if cell_timeout_seconds > 0:
                                raw = _run_one_isolated(
                                    task_index,
                                    env_name,
                                    run_kwargs,
                                    cell_timeout_seconds,
                                )
                            else:
                                raw = run_one(
                                    _make_input(task_index, env_name=env_name),
                                    **run_kwargs,
                                )

                            task_id = str(task_index)

                            res = raw[task_id]
                            mut = res.get("schema_mutation", {}) or {}
                            record.update(
                                {
                                    "status": "ok",
                                    "reward": res.get("reward"),
                                    "num_actions": len(res.get("taken_actions", [])),
                                    "wallclock_s": res.get("wallclock_s"),
                                    "mutation_applied": mut.get("applied"),
                                    "mutation_tool": mut.get("tool_name"),
                                    "mutation_note": mut.get("note"),
                                    "mutation_meta": mut,
                                    "observability_level": res.get(
                                        "observability_level",
                                        record.get("observability_level"),
                                    ),
                                    "c4_runtime_mode": res.get(
                                        "c4_runtime_mode",
                                        record.get("c4_runtime_mode"),
                                    ),
                                    "oracle_rule_violation": res.get("oracle_rule_violation"),
                                    "visible_policy_error": res.get("visible_policy_error"),
                                    "generic_error_visible": res.get("generic_error_visible"),
                                    "structured_policy_error_visible": res.get("structured_policy_error_visible"),
                                    "migration_note_visible": res.get("migration_note_visible"),
                                    "hidden_business_rule_violation": res.get("hidden_business_rule_violation"),
                                    "recovery_attempted": res.get("recovery_attempted"),
                                    "recovery_success": res.get("recovery_success"),
                                    "final_reward": res.get("final_reward", res.get("reward")),
                                    "failure_mode": res.get("failure_mode"),
                                    "target_tool": res.get("target_tool", mut.get("tool_name")),
                                    "intent_aligned": res.get("intent_aligned", record.get("intent_aligned", False)),
                                    "oracle_rule_error": res.get("oracle_rule_error"),
                                    "oracle_rule_action": res.get("oracle_rule_action"),
                                    "oracle_rule_mode": res.get("oracle_rule_mode"),
                                    "oracle_force_zero": res.get("oracle_force_zero"),
                                    "runtime_policy_violation": res.get("runtime_policy_violation"),
                                    "runtime_policy_error": res.get("runtime_policy_error"),
                                    "runtime_policy_action": res.get("runtime_policy_action"),
                                    "runtime_policy_mode": res.get("runtime_policy_mode"),
                                    "runtime_policy_force_zero": res.get("runtime_policy_force_zero"),
                                    "raw": res,


                                }
                            )
                            ok += 1
                        except Exception as e:  # noqa: BLE001
                            err = "".join(
                                traceback.format_exception_only(type(e), e)
                            ).strip()
                            tb = traceback.format_exc(limit=5)
                            status = "timeout" if isinstance(e, TimeoutError) else "error"
                            record.update(
                                {
                                    "status": status,
                                    "error_type": type(e).__name__,
                                    "error": err,
                                    "traceback": tb,
                                }
                            )

                            failed += 1
                            if _is_quota_error(err + "\n" + tb):
                                quota_hit = True
                                record["quota_hit"] = True
                        finally:
                            record["elapsed_s"] = round(time.time() - t0, 2)
                            f.write(json.dumps(record, ensure_ascii=False) + "\n")
                            f.flush()
                            print(f"    -> {_summarize(record)} ({record['elapsed_s']}s)", flush=True)

                        if quota_hit and stop_on_quota:
                            print("\n[ABORT] API quota/balance error detected. 请充值后继续。", flush=True)
                            print(f"[partial] ok={ok} failed={failed} skipped={skipped} written={out_path}", flush=True)
                            return 2

    print(f"\n[done] ok={ok} failed={failed} skipped={skipped} total={total} out={out_path}", flush=True)
    return 0 if failed == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", default="0,1")
    p.add_argument(
        "--models",
        default="dashscope/qwen3.7-max-2026-06-08,dashscope/qwen-flash",
    )
    p.add_argument(
        "--mutations",
        default="baseline,A1_identifier_rename,C1_unit_scale_drift",
        help="comma-separated; use 'baseline' or 'none' for no mutation",
    )
    p.add_argument("--seeds", default="0")
    p.add_argument("--env", default="retail", choices=["retail", "airline"], help="tau-bench domain")

    p.add_argument(
        "--out",
        default="runs/schema_mutation/day4_smoke.jsonl",
    )
    p.add_argument("--env-user-model", default=os.getenv("SCHEMA_MUTATION_USER_MODEL", "dashscope/qwen-flash"))
    p.add_argument("--env-user-provider", default=os.getenv("SCHEMA_MUTATION_USER_PROVIDER", "dashscope"))
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--max-num-steps", type=int, default=30)
    p.add_argument(
        "--cell-timeout-seconds",
        type=int,
        default=0,
        help="Run each cell in a subprocess and mark status=timeout after N seconds; 0 disables isolation.",
    )

    p.add_argument("--exposure-map", default=None, help="JSON from trajectory_extractor.py")
    p.add_argument("--target-tools", default=None, help="comma-separated explicit mutation target tools")
    p.add_argument("--avoid-tools", default=None, help="comma-separated explicit tools to avoid")
    p.add_argument("--business-rule-intent", default=None, help="explicit C4 business-rule intent for runtime oracle")
    p.add_argument("--business-rule-drift", default=None, help="explicit C4 business-rule drift text for runtime oracle")

    p.add_argument(
        "--target-policy",
        default="random",
        choices=["random", "used_tool", "unused_tool", "intent_aligned", "unused_intent_aligned", "random_intent_aligned"],
        help="random = current protocol; used_tool = mutate baseline-used tools; unused_tool = negative control; intent_aligned = used_tool + ta<REDACTED_SECRET> C4 drift; unused_intent_aligned/random_intent_aligned are runtime C4 controls",
    )
    p.add_argument(
        "--c4-runtime-mode",
        default="visible",
        choices=[
            "visible",
            "silent",
            "visible_policy_violation",
            "silent_business_rule_drift",
            "C4a",
            "C4b",
            "generic_error",
            "structured_policy_error",
            "migration_note",
        ] + OBSERVABILITY_LEVELS,
        help="C4 runtime semantics: visible/C4a exposes policy error; silent/C4b hides the policy drift and only changes final validity.",
    )
    p.add_argument(
        "--observability-level",
        default=None,
        choices=OBSERVABILITY_LEVELS,
        help="Canonical C4 observability level for the O0-O4 gradient.",
    )
    p.add_argument("--dry-run", action="store_true", help="print planned cells without calling APIs or writing JSONL")
    p.add_argument("--keep-going-on-quota", action="store_true")

    p.add_argument(
        "--skip-existing-ok",
        action="store_true",
        help="If --out already exists, skip cells that already have status=ok.",
    )
    args = p.parse_args()

    tasks = [int(x) for x in _parse_csv(args.tasks)]
    models = _parse_csv(args.models)
    raw_mutations = _parse_csv(args.mutations)
    mutations: list[str | None] = [
        None if x.lower() in {"baseline", "none", "null"} else x
        for x in raw_mutations
    ]
    seeds = [int(x) for x in _parse_csv(args.seeds)]
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = _REPO_ROOT / out_path

    exposure_map = None
    if args.exposure_map:
        exp_path = Path(args.exposure_map)
        if not exp_path.is_absolute():
            exp_path = _REPO_ROOT / exp_path
        exposure_map = json.loads(exp_path.read_text(encoding="utf-8"))

    return run_batch(
        tasks=tasks,
        models=models,
        mutations=mutations,
        seeds=seeds,
        out_path=out_path,
        env_user_model=args.env_user_model,
        env_user_provider=args.env_user_provider,
        temperature=args.temperature,
        stop_on_quota=not args.keep_going_on_quota,
        skip_existing_ok=args.skip_existing_ok,
        exposure_map=exposure_map,
        target_policy=args.target_policy,
        c4_runtime_mode=args.c4_runtime_mode,
        observability_level=args.observability_level,
        env_name=args.env,
        max_num_steps=args.max_num_steps,
        cell_timeout_seconds=args.cell_timeout_seconds,
        target_tools=_parse_csv(args.target_tools) if args.target_tools else None,
        avoid_tools=_parse_csv(args.avoid_tools) if args.avoid_tools else None,
        business_rule_intent=args.business_rule_intent,
        business_rule_drift=args.business_rule_drift,
        dry_run=args.dry_run,
    )






if __name__ == "__main__":
    raise SystemExit(main())
