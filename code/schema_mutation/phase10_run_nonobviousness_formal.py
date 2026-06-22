"""Run one Phase 10C non-obviousness formal shard.

This runner intentionally writes outside Phase 5/8 and outside the Phase 10B
smoke directory. It uses the same single-cell execution path as the smoke
runner, but stores formal outputs under:

`runs/schema_mutation/phase10/phase10c/nonobviousness_formal/`.
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
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "runs" / "schema_mutation" / "phase10" / "phase10c" / "nonobviousness_formal"
STATUS_DIR = OUT_DIR / "status"
RAW_DIR = OUT_DIR / "raw"
LOG_DIR = OUT_DIR / "logs"
META_DIR = OUT_DIR / "metadata"

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

STOP_LIMITS = {"provider_error": 5, "timeout": 5, "failed": 5}
PROVIDER_KEY_ENV = {
    "deepseek": ("DEEPSEEK_API_KEY",),
    "dashscope": ("DASHSCOPE_API_KEY",),
}
PROVIDER_ERROR_PATTERNS = (
    "api_key",
    "api key",
    "quota",
    "balance",
    "billing",
    "insufficient",
    "unauthorized",
    "forbidden",
    "provider",
    "base_url",
    "base url",
    "connection",
)
FORBIDDEN_MODEL_MARKERS = ("gpt", "grok", "wyzlab", "wyzai")
TERMINAL_STATUSES = {"ok", "provider_error", "timeout", "failed", "not_run"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def provider_env() -> dict[str, str]:
    env = dict(os.environ)
    aliases = {
        "DEEPSEEK_API_BASE": "DEEPSEEK_BASE_URL",
        "DASHSCOPE_API_BASE": "DASHSCOPE_BASE_URL",
    }
    for src, dst in aliases.items():
        if env.get(src) and not env.get(dst):
            env[dst] = env[src]
    return env


def classify_error(text: str) -> str:
    low = text.lower()
    if "timeouterror" in low or "timeout" in low:
        return "timeout"
    if any(pattern in low for pattern in PROVIDER_ERROR_PATTERNS):
        return "provider_error"
    return "failed"


def base_status(cell: dict[str, Any], status: str = "pending") -> dict[str, Any]:
    return {
        "cell_key": cell.get("cell_key"),
        "status": status,
        "env": cell.get("env"),
        "model": cell.get("model"),
        "provider": cell.get("provider"),
        "task_id": cell.get("task_id"),
        "seed": cell.get("seed"),
        "condition": cell.get("condition"),
        "condition_family": cell.get("condition_family"),
        "agent_prompt_variant": cell.get("agent_prompt_variant"),
        "scaffold_type": None,
        "observability_level": cell.get("observability_level"),
        "mutation_name": cell.get("mutation_name"),
        "semantic_class": cell.get("semantic_class"),
        "baseline_success": cell.get("baseline_success"),
        "schema_changed": cell.get("schema_changed"),
        "typed_client_compatible": cell.get("typed_client_compatible"),
        "runner_ready": cell.get("runner_ready"),
        "requires_runner_extension": cell.get("requires_runner_extension"),
        "source_o0_cell_key": cell.get("source_o0_cell_key"),
        "source_baseline_cell_key": cell.get("source_baseline_cell_key"),
        "target_tool": cell.get("target_tool"),
        "reward": None,
        "mutation_success": None,
        "visible_policy_error": False,
        "migration_note_visible": cell.get("observability_level") == "O4_migration_note",
        "oracle_rule_violation": False,
        "hidden_business_rule_violation": False,
        "recovery_attempted": False,
        "recovery_success": False,
        "failure_mode": None,
        "num_actions": 0,
        "error_message": None,
        "elapsed_s": 0.0,
        "phase": "phase10c",
    }


def has_forbidden_model_marker(cell: dict[str, Any]) -> bool:
    text = f"{cell.get('provider', '')}/{cell.get('model', '')}".lower()
    return any(marker in text for marker in FORBIDDEN_MODEL_MARKERS)


def validate_shard(cells: list[dict[str, Any]], shard_path: Path) -> list[str]:
    errors: list[str] = []
    if "smoke" in shard_path.name.lower():
        errors.append("formal runner refuses to run a smoke shard")
    if not cells:
        errors.append("formal shard is empty")
    for cell in cells:
        cell_key = cell.get("cell_key")
        if str(cell.get("phase")) != "phase10":
            errors.append(f"{cell_key}: phase is not phase10")
        if cell.get("experiment") != "nonobviousness_control":
            errors.append(f"{cell_key}: experiment is not nonobviousness_control")
        if cell.get("baseline_success") is not True:
            errors.append(f"{cell_key}: baseline_success is not true")
        if cell.get("schema_changed") is not False:
            errors.append(f"{cell_key}: schema_changed is not false")
        if cell.get("execution_mode") == "local_fake" or cell.get("fake_run"):
            errors.append(f"{cell_key}: fake_run/local_fake appears")
        if has_forbidden_model_marker(cell):
            errors.append(f"{cell_key}: forbidden GPT/WYZ/Grok model or provider appears")
        condition = str(cell.get("condition"))
        drift = str(cell.get("business_rule_drift") or "")
        variant = str(cell.get("agent_prompt_variant") or "")
        level = str(cell.get("observability_level") or "")
        if condition in {"O0_increased_reasoning_budget", "O0_reflection_scaffold"}:
            if variant == "rule_visible_preamble":
                errors.append(f"{cell_key}: O0 condition has rule-visible prompt variant")
            if level != "O0_silent":
                errors.append(f"{cell_key}: O0 condition is not O0_silent")
            if "evolved API rule is" in drift:
                errors.append(f"{cell_key}: O0 drift text appears prompt-like")
        if condition == "rule_in_tool_preamble_upper_bound":
            if variant != "rule_visible_preamble":
                errors.append(f"{cell_key}: upper-bound condition lacks rule-visible prompt variant")
            if level != "O4_migration_note":
                errors.append(f"{cell_key}: upper-bound condition is not O4_migration_note")
    return errors


def preflight(cells: list[dict[str, Any]], shard_path: Path) -> list[str]:
    issues = validate_shard(cells, shard_path)
    try:
        __import__("tau_bench")
    except Exception as exc:  # noqa: BLE001
        issues.append(f"tau_bench dependency unavailable: {type(exc).__name__}: {exc}")
    env = provider_env()
    for provider in sorted({str(cell.get("provider") or "") for cell in cells}):
        key_envs = PROVIDER_KEY_ENV.get(provider, ())
        if key_envs and not any(env.get(key) for key in key_envs):
            issues.append(f"{provider} credentials unavailable: {' or '.join(key_envs)} is not set")
    return issues


def kill_process_tree(proc: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        proc.kill()


def append_log(path: Path, cell: dict[str, Any], cmd: list[str], stdout: str, stderr: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n=== {cell.get('cell_key')} {time.strftime('%Y-%m-%dT%H:%M:%S')} ===\n")
        f.write("CMD " + " ".join(cmd) + "\n")
        if stdout:
            f.write("--- stdout ---\n" + stdout[-8000:] + "\n")
        if stderr:
            f.write("--- stderr ---\n" + stderr[-8000:] + "\n")


def run_cell(cell: dict[str, Any], log_path: Path, timeout_s: int) -> tuple[dict[str, Any], dict[str, Any] | None]:
    status = base_status(cell)
    env = provider_env()
    run_kwargs = {
        "agent_model_name": cell.get("model"),
        "mutation_type": cell.get("mutation_name"),
        "seed": cell.get("seed"),
        "temperature": 0.0,
        "env_user_model": os.getenv("SCHEMA_MUTATION_USER_MODEL", "dashscope/qwen-flash"),
        "env_user_provider": os.getenv("SCHEMA_MUTATION_USER_PROVIDER", "dashscope"),
        "c4_runtime_mode": "silent" if cell.get("observability_level") == "O0_silent" else "migration_note",
        "observability_level": cell.get("observability_level"),
        "target_policy": cell.get("protocol") or "intent_aligned",
        "max_num_steps": cell.get("max_num_steps", 30),
        "target_tools": ",".join(str(x) for x in cell.get("target_tools", []) if str(x)),
        "business_rule_intent": cell.get("business_rule_intent"),
        "business_rule_drift": cell.get("business_rule_drift"),
        "phase10_nonobviousness": True,
        "agent_prompt_variant": cell.get("agent_prompt_variant") or "standard",
    }
    with tempfile.TemporaryDirectory(prefix="phase10c_nonobv_") as tmp:
        payload = {
            "task_index": int(cell["task_id"]),
            "env": cell.get("env", "retail"),
            "run_kwargs": run_kwargs,
        }
        payload_path = Path(tmp) / "payload.json"
        result_path = Path(tmp) / "result.json"
        payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        cmd = [
            sys.executable,
            "-m",
            "code.schema_mutation.single_cell_runner",
            str(payload_path),
            str(result_path),
        ]
        t0 = time.time()
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            kill_process_tree(proc)
            stdout, stderr = proc.communicate()
            status.update(
                {
                    "status": "timeout",
                    "elapsed_s": round(time.time() - t0, 2),
                    "error_message": f"cell timeout after {timeout_s}s",
                }
            )
            append_log(log_path, cell, cmd, stdout, stderr)
            return status, None
        append_log(log_path, cell, cmd, stdout, stderr)
        if proc.returncode != 0 or not result_path.exists():
            text = stderr or stdout or f"single_cell_runner exited {proc.returncode}"
            status.update(
                {
                    "status": classify_error(text),
                    "elapsed_s": round(time.time() - t0, 2),
                    "error_message": text[:2000],
                }
            )
            return status, None
        raw = json.loads(result_path.read_text(encoding="utf-8"))
        rec = raw[str(cell["task_id"])]
        reward = rec.get("final_reward", rec.get("reward"))
        status.update(
            {
                "status": "ok",
                "reward": reward,
                "mutation_success": bool(float(reward or 0) > 0),
                "visible_policy_error": bool(rec.get("visible_policy_error")),
                "migration_note_visible": bool(rec.get("migration_note_visible")),
                "oracle_rule_violation": bool(rec.get("oracle_rule_violation")),
                "hidden_business_rule_violation": bool(rec.get("hidden_business_rule_violation")),
                "recovery_attempted": bool(rec.get("recovery_attempted")),
                "recovery_success": bool(rec.get("recovery_success")),
                "failure_mode": rec.get("failure_mode"),
                "num_actions": len(rec.get("taken_actions", [])),
                "scaffold_type": rec.get("scaffold_type"),
                "elapsed_s": round(time.time() - t0, 2),
            }
        )
        return status, {"cell": cell, "raw": raw}


def existing_terminal_statuses(path: Path) -> set[str]:
    keys: set[str] = set()
    if not path.exists():
        return keys
    for row in read_jsonl(path):
        if str(row.get("status")) in TERMINAL_STATUSES:
            keys.add(str(row.get("cell_key")))
    return keys


def write_metadata(path: Path, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_preflight_stop(
    cells: list[dict[str, Any]],
    issues: list[str],
    status_path: Path,
    raw_path: Path,
    metadata_path: Path,
    skip_existing: bool,
) -> int:
    if not skip_existing:
        for path in (status_path, raw_path):
            if path.exists():
                path.unlink()
    message = "; ".join(issues)
    for cell in cells:
        status = base_status(cell, status="not_run")
        status["error_message"] = message
        append_jsonl(status_path, status)
    metadata = {
        "status": "preflight_stopped",
        "issues": issues,
        "planned_cells": len(cells),
        "actually_run_cells": 0,
        "skipped_existing_cells": 0,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    write_metadata(metadata_path, metadata)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    global OUT_DIR, STATUS_DIR, RAW_DIR, LOG_DIR, META_DIR

    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--force", action="store_true", help="ignore dependency/key preflight issues")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.max_workers != 1:
        raise SystemExit("Phase 10C formal runner currently supports --max-workers 1")
    if args.output_dir:
        out_dir = Path(args.output_dir)
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir
        OUT_DIR = out_dir
        STATUS_DIR = OUT_DIR / "status"
        RAW_DIR = OUT_DIR / "raw"
        LOG_DIR = OUT_DIR / "logs"
        META_DIR = OUT_DIR / "metadata"

    shard = Path(args.shard)
    if not shard.is_absolute():
        shard = ROOT / shard
    cells = read_jsonl(shard)
    shard_name = shard.stem
    status_path = STATUS_DIR / f"{shard_name}_status.jsonl"
    raw_path = RAW_DIR / f"{shard_name}_raw.jsonl"
    log_path = LOG_DIR / f"{shard_name}.log"
    metadata_path = META_DIR / f"{shard_name}_metadata.json"

    print(f"[phase10c-formal] shard={shard}")
    print(f"[phase10c-formal] cells={len(cells)} max_workers={args.max_workers}")
    print(f"[phase10c-formal] status={status_path}")
    print(f"[phase10c-formal] raw={raw_path}")

    if args.dry_run:
        for cell in cells:
            print(
                "PLAN "
                f"{cell.get('cell_key')} env={cell.get('env')} model={cell.get('model')} "
                f"task={cell.get('task_id')} seed={cell.get('seed')} "
                f"condition={cell.get('condition')} mutation={cell.get('mutation_name')}"
            )
        return 0

    for directory in (STATUS_DIR, RAW_DIR, LOG_DIR, META_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    issues = preflight(cells, shard)
    if issues and not args.force:
        return write_preflight_stop(cells, issues, status_path, raw_path, metadata_path, args.skip_existing)

    if not args.skip_existing:
        for path in (status_path, raw_path, log_path):
            if path.exists():
                path.unlink()

    existing = existing_terminal_statuses(status_path) if args.skip_existing else set()
    counts: Counter[str] = Counter()
    run_n = 0
    skipped_n = 0
    stopped = False
    for cell in cells:
        cell_key = str(cell.get("cell_key"))
        if cell_key in existing:
            skipped_n += 1
            print(f"SKIP {cell_key}")
            continue
        try:
            status, raw = run_cell(cell, log_path, timeout_s=int(cell.get("timeout_seconds") or 900) + 30)
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc(limit=8)
            text = f"{type(exc).__name__}: {exc}\n{tb}"
            status = base_status(cell)
            status.update({"status": classify_error(text), "error_message": text[:2000], "elapsed_s": 0.0})
            raw = None
        run_n += 1
        counts[str(status["status"])] += 1
        append_jsonl(status_path, status)
        if raw is not None:
            append_jsonl(raw_path, raw)
        print(f"{status['status'].upper()} {status.get('cell_key')} reward={status.get('reward')}")
        if any(counts[k] >= v for k, v in STOP_LIMITS.items()):
            stopped = True
            break

    completed = run_n + skipped_n == len(cells) and not stopped
    metadata = {
        "status": "completed" if completed else "stopped_by_stop_rule",
        "planned_cells": len(cells),
        "actually_run_cells": run_n,
        "skipped_existing_cells": skipped_n,
        "status_counts": dict(counts),
        "stop_limits": STOP_LIMITS,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    write_metadata(metadata_path, metadata)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0 if completed else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        META_DIR.mkdir(parents=True, exist_ok=True)
        tb = traceback.format_exc(limit=8)
        (META_DIR / "runner_failed_metadata.json").write_text(
            json.dumps(
                {
                    "status": "runner_failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": tb,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
