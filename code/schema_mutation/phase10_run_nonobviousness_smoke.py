"""Run only the Phase 10B non-obviousness smoke shard.

The runner is intentionally isolated from Phase 5 status/raw directories. It
uses the existing single-cell execution path but writes all Phase 10B outputs to
`runs/schema_mutation/phase10/phase10b/nonobviousness_smoke/`.
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
OUT_DIR = ROOT / "runs" / "schema_mutation" / "phase10" / "phase10b" / "nonobviousness_smoke"
RESULTS = OUT_DIR / "smoke_results.jsonl"
RAW = OUT_DIR / "smoke_raw.jsonl"
LOG = OUT_DIR / "smoke_run.log"

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

STOP_LIMITS = {"provider_error": 3, "timeout": 3, "failed": 3}
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
    if "modulenotfounderror" in low or "no module named" in low:
        return "failed"
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
        "agent_prompt_variant": cell.get("agent_prompt_variant"),
        "scaffold_type": None,
        "observability_level": cell.get("observability_level"),
        "mutation_name": cell.get("mutation_name"),
        "semantic_class": cell.get("semantic_class"),
        "baseline_success": cell.get("baseline_success"),
        "runner_ready": cell.get("runner_ready"),
        "requires_runner_extension": cell.get("requires_runner_extension"),
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
        "phase": "phase10b",
    }


def validate_shard(cells: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(cells) > 20:
        errors.append(f"smoke shard has {len(cells)} cells; expected <= 20")
    for cell in cells:
        if str(cell.get("phase")) != "phase10":
            errors.append(f"{cell.get('cell_key')}: phase is not phase10")
        if not cell.get("baseline_success"):
            errors.append(f"{cell.get('cell_key')}: baseline_success=false")
        if cell.get("execution_mode") == "local_fake" or cell.get("fake_run"):
            errors.append(f"{cell.get('cell_key')}: fake_run/local_fake appears")
        condition = str(cell.get("condition"))
        drift = str(cell.get("business_rule_drift") or "")
        variant = str(cell.get("agent_prompt_variant") or "")
        if condition in {"O0_increased_reasoning_budget", "O0_reflection_scaffold"} and variant == "rule_visible_preamble":
            errors.append(f"{cell.get('cell_key')}: O0 condition has rule-visible prompt variant")
        if condition in {"O0_increased_reasoning_budget", "O0_reflection_scaffold"} and cell.get("observability_level") != "O0_silent":
            errors.append(f"{cell.get('cell_key')}: O0 condition is not O0_silent")
        if condition in {"O0_increased_reasoning_budget", "O0_reflection_scaffold"} and "evolved API rule is" in drift:
            errors.append(f"{cell.get('cell_key')}: O0 drift text appears prompt-like")
    return errors


def preflight(cells: list[dict[str, Any]]) -> list[str]:
    issues = validate_shard(cells)
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


def run_cell(cell: dict[str, Any], timeout_s: int) -> tuple[dict[str, Any], dict[str, Any] | None]:
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
    with tempfile.TemporaryDirectory(prefix="phase10_smoke_") as tmp:
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
            proc.kill()
            stdout, stderr = proc.communicate()
            status.update(
                {
                    "status": "timeout",
                    "elapsed_s": round(time.time() - t0, 2),
                    "error_message": f"cell timeout after {timeout_s}s",
                }
            )
            return status, None
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"\n=== {cell.get('cell_key')} {time.strftime('%Y-%m-%dT%H:%M:%S')} ===\n")
            f.write("CMD " + " ".join(cmd) + "\n")
            if stdout:
                f.write("--- stdout ---\n" + stdout[-8000:] + "\n")
            if stderr:
                f.write("--- stderr ---\n" + stderr[-8000:] + "\n")
        if proc.returncode != 0 or not result_path.exists():
            text = stderr or stdout or f"single_cell_runner exited {proc.returncode}"
            status.update(
                {
                    "status": classify_error(text),
                    "elapsed_s": round(time.time() - t0, 2),
                    "error_message": text[:1000],
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


def write_preflight_stop(cells: list[dict[str, Any]], issues: list[str]) -> int:
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    if RESULTS.exists():
        RESULTS.unlink()
    if RAW.exists():
        RAW.unlink()
    message = "; ".join(issues)
    for cell in cells:
        status = base_status(cell, status="not_run")
        status["error_message"] = message
        append_jsonl(RESULTS, status)
    metadata = {
        "status": "preflight_stopped",
        "issues": issues,
        "planned_cells": len(cells),
        "actually_run_cells": 0,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (OUT_DIR / "smoke_run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", required=True)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--force", action="store_true", help="ignore dependency/key preflight issues")
    args = parser.parse_args()
    if args.max_workers != 1:
        raise SystemExit("Phase 10B smoke runner only supports --max-workers 1")
    shard = Path(args.shard)
    if not shard.is_absolute():
        shard = ROOT / shard
    cells = read_jsonl(shard)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    issues = preflight(cells)
    if issues and not args.force:
        return write_preflight_stop(cells, issues)
    if RESULTS.exists() and not args.skip_existing:
        RESULTS.unlink()
    if RAW.exists() and not args.skip_existing:
        RAW.unlink()
    counts: Counter[str] = Counter()
    run_n = 0
    for cell in cells:
        status, raw = run_cell(cell, timeout_s=int(cell.get("timeout_seconds") or 900) + 30)
        run_n += 1
        counts[str(status["status"])] += 1
        append_jsonl(RESULTS, status)
        if raw is not None:
            append_jsonl(RAW, raw)
        print(f"{status['status'].upper()} {status.get('cell_key')} reward={status.get('reward')}")
        if any(counts[k] >= v for k, v in STOP_LIMITS.items()):
            break
    metadata = {
        "status": "completed" if run_n == len(cells) else "stopped_by_stop_rule",
        "planned_cells": len(cells),
        "actually_run_cells": run_n,
        "status_counts": dict(counts),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (OUT_DIR / "smoke_run_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        tb = traceback.format_exc(limit=8)
        (OUT_DIR / "smoke_run_metadata.json").write_text(
            json.dumps(
                {
                    "status": "runner_failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": tb,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
