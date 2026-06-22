"""Execute one Phase 5 shard with per-cell status logging.

Default execution is conservative: one worker, one subprocess per live cell, and
cell failures are written as status records rather than aborting the shard.
Cells with ``execution_mode=local_fake`` are local smoke tests and do not call
external APIs.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
import threading
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

RUNS = _REPO_ROOT / "runs" / "schema_mutation" / "phase5"
RAW_DIR = RUNS / "raw"
STATUS_DIR = RUNS / "status"
LOG_DIR = RUNS / "logs"

PROVIDER_KEY_ENV = {
    "deepseek": ("DEEPSEEK_API_KEY",),
    "dashscope": ("DASHSCOPE_API_KEY",),
    "wyzlab": ("WYZAI_API_KEY", "WYZLAB_API_KEY"),
    "wyzai": ("WYZAI_API_KEY", "WYZLAB_API_KEY"),
    "mimo": ("MIMO_API_KEY",),
}

PROVIDER_BASE_ALIASES = {
    "DEEPSEEK_API_BASE": "DEEPSEEK_BASE_URL",
    "DASHSCOPE_API_BASE": "DASHSCOPE_BASE_URL",
    "WYZAI_API_BASE": "WYZAI_BASE_URL",
    "WYZLAB_API_BASE": "WYZLAB_BASE_URL",
    "MIMO_API_BASE": "MIMO_BASE_URL",
}

PROVIDER_ERROR_PATTERNS = [
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
    "timeout",
]


def _classify_error(text: str) -> str:
    """Classify execution errors without treating local dependency failures as provider failures."""
    low = text.lower()
    if "modulenotfounderror" in low or "no module named" in low:
        return "failed"
    if _looks_provider_error(text):
        return "provider_error"
    return "failed"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"[warn] {path}:{line_no}: {exc}")
    return rows


def _append_jsonl(path: Path, row: dict[str, Any], lock: threading.Lock) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _terminal_existing(path: Path) -> set[str]:
    keys: set[str] = set()
    if not path.exists():
        return keys
    for row in _read_jsonl(path):
        if row.get("status") in {"ok", "provider_error", "timeout", "failed"}:
            keys.add(str(row.get("cell_key")))
    return keys


def _reward(row: dict[str, Any]) -> float | None:
    value = row.get("final_reward", row.get("reward"))
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _success(row: dict[str, Any]) -> bool | None:
    reward = _reward(row)
    return None if reward is None else reward > 0


def _provider_env() -> dict[str, str]:
    env = dict(os.environ)
    for api_base, base_url in PROVIDER_BASE_ALIASES.items():
        if env.get(api_base) and not env.get(base_url):
            env[base_url] = env[api_base]
    if env.get("WYZAI_API_KEY") and not env.get("WYZLAB_API_KEY"):
        env["WYZLAB_API_KEY"] = env["WYZAI_API_KEY"]
    return env


def _looks_provider_error(text: str) -> bool:
    low = text.lower()
    return any(pattern in low for pattern in PROVIDER_ERROR_PATTERNS)


def _base_status(cell: dict[str, Any]) -> dict[str, Any]:
    return {
        "cell_key": cell.get("cell_key"),
        "status": "pending",
        "env": cell.get("env"),
        "model": cell.get("model"),
        "provider": cell.get("provider"),
        "task_id": cell.get("task_id"),
        "seed": cell.get("seed"),
        "condition": cell.get("condition"),
        "observability_level": cell.get("observability_level"),
        "mutation_class": cell.get("mutation_class"),
        "mutation_name": cell.get("mutation_name"),
        "semantic_class": cell.get("semantic_class"),
        "protocol": cell.get("protocol"),
        "schema_changed": cell.get("schema_changed"),
        "typed_client_compatible": cell.get("typed_client_compatible"),
        "source_baseline_cell_key": cell.get("source_baseline_cell_key"),
        "baseline_success": cell.get("baseline_success"),
        "mutation_success": None,
        "reward": None,
        "visible_policy_error": False,
        "generic_error_visible": False,
        "structured_policy_error_visible": False,
        "migration_note_visible": cell.get("observability_level") == "O4_migration_note",
        "oracle_rule_violation": False,
        "hidden_business_rule_violation": False,
        "recovery_attempted": False,
        "recovery_success": False,
        "failure_mode": None,
        "num_actions": 0,
        "timeout": False,
        "max_step_cutoff": False,
        "target_tool_called": None,
        "target_tool": cell.get("target_tool"),
        "error_message": None,
        "execution_mode": cell.get("execution_mode", "live"),
        "fake_run": cell.get("execution_mode") == "local_fake",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def _fake_status(cell: dict[str, Any]) -> dict[str, Any]:
    status = _base_status(cell)
    condition = str(cell.get("condition"))
    mutation = cell.get("mutation_name")
    baseline = mutation is None or condition == "baseline"
    if baseline:
        reward = 1.0
        failure_mode = None
        visible = False
        generic = False
        structured = False
        hidden = False
        recovery_attempted = False
        recovery_success = False
    elif condition == "O0_silent":
        reward = 0.0
        failure_mode = "silent_failure"
        visible = False
        generic = False
        structured = False
        hidden = True
        recovery_attempted = False
        recovery_success = False
    elif condition == "O2_policy_error":
        reward = 1.0
        failure_mode = None
        visible = True
        generic = False
        structured = False
        hidden = False
        recovery_attempted = True
        recovery_success = True
    else:
        reward = 1.0
        failure_mode = None
        visible = condition in {"O1_generic_error", "O2_policy_error", "O3_structured_policy_error", "O4_migration_note"}
        generic = condition == "O1_generic_error"
        structured = condition == "O3_structured_policy_error"
        hidden = False
        recovery_attempted = not baseline
        recovery_success = not baseline

    status.update(
        {
            "status": "ok",
            "baseline_success": True if baseline else cell.get("baseline_success", True),
            "mutation_success": None if baseline else reward > 0,
            "reward": reward,
            "visible_policy_error": visible,
            "generic_error_visible": generic,
            "structured_policy_error_visible": structured,
            "migration_note_visible": condition == "O4_migration_note",
            "oracle_rule_violation": bool(hidden),
            "hidden_business_rule_violation": bool(hidden),
            "recovery_attempted": recovery_attempted,
            "recovery_success": recovery_success,
            "failure_mode": failure_mode,
            "num_actions": 3 if baseline else 4,
            "target_tool_called": not baseline,
            "target_tool": "fake_target_tool" if not baseline else None,
            "elapsed_s": 0.01,
        }
    )
    return status


def _batch_command(cell: dict[str, Any], out_path: Path) -> list[str]:
    mutation = cell.get("mutation_name") or "baseline"
    protocol = cell.get("protocol")
    if not protocol or protocol == "none":
        protocol = "random"
    cmd = [
        sys.executable,
        "-m",
        "code.schema_mutation.batch_runner",
        "--env",
        str(cell["env"]),
        "--tasks",
        str(cell["task_id"]),
        "--models",
        str(cell["model"]),
        "--mutations",
        str(mutation),
        "--seeds",
        str(cell["seed"]),
        "--out",
        str(out_path),
        "--target-policy",
        str(protocol),
        "--max-num-steps",
        str(cell.get("max_num_steps", 30)),
        "--cell-timeout-seconds",
        str(cell.get("timeout_seconds", 600)),
        "--keep-going-on-quota",
    ]
    if cell.get("observability_level"):
        cmd.extend(["--observability-level", str(cell["observability_level"])])
    if cell.get("unused_target_tool"):
        cmd.extend(["--target-tools", str(cell["unused_target_tool"])])
    elif cell.get("target_tools"):
        target_tools = cell["target_tools"]
        if isinstance(target_tools, list):
            target_tools = ",".join(str(x) for x in target_tools)
        cmd.extend(["--target-tools", str(target_tools)])
    if cell.get("baseline_used_tools"):
        avoid_tools = cell["baseline_used_tools"]
        if isinstance(avoid_tools, list):
            avoid_tools = ",".join(str(x) for x in avoid_tools)
        cmd.extend(["--avoid-tools", str(avoid_tools)])
    if cell.get("business_rule_intent"):
        cmd.extend(["--business-rule-intent", str(cell["business_rule_intent"])])
    if cell.get("business_rule_drift"):
        cmd.extend(["--business-rule-drift", str(cell["business_rule_drift"])])
    return cmd


def _convert_batch_record(cell: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    status = _base_status(cell)
    batch_status = record.get("status")
    reward = _reward(record)
    if batch_status == "ok":
        out_status = "ok"
    elif batch_status == "timeout":
        out_status = "timeout"
    else:
        text = "\n".join(str(record.get(k, "")) for k in ("error", "traceback", "error_type"))
        out_status = _classify_error(text)
    mutation_success = None if cell.get("mutation_name") is None else (reward > 0 if reward is not None else None)
    raw = record.get("raw") if isinstance(record.get("raw"), dict) else {}
    taken_actions = raw.get("taken_actions") if isinstance(raw, dict) else None
    mutation_tool = record.get("target_tool") or record.get("mutation_tool")
    target_tool_called = None
    if mutation_tool and isinstance(taken_actions, list):
        target_tool_called = any(str(mutation_tool) in json.dumps(a, ensure_ascii=False) for a in taken_actions)
    status.update(
        {
            "status": out_status,
            "baseline_success": _success(record) if cell.get("mutation_name") is None else cell.get("baseline_success"),
            "mutation_success": mutation_success,
            "reward": reward,
            "visible_policy_error": bool(record.get("visible_policy_error")),
            "generic_error_visible": bool(record.get("generic_error_visible")),
            "structured_policy_error_visible": bool(record.get("structured_policy_error_visible")),
            "migration_note_visible": bool(record.get("migration_note_visible")),
            "oracle_rule_violation": bool(record.get("oracle_rule_violation")),
            "hidden_business_rule_violation": bool(record.get("hidden_business_rule_violation")),
            "recovery_attempted": bool(record.get("recovery_attempted")),
            "recovery_success": bool(record.get("recovery_success")),
            "failure_mode": record.get("failure_mode"),
            "num_actions": int(record.get("num_actions") or 0),
            "timeout": out_status == "timeout",
            "max_step_cutoff": (record.get("failure_mode") == "max_step_cutoff"),
            "target_tool_called": target_tool_called,
            "target_tool": mutation_tool,
            "error_message": record.get("error"),
            "elapsed_s": record.get("elapsed_s"),
            "batch_status": batch_status,
            "raw_record_status": record.get("status"),
            "source_exposed_o0_cell_key": cell.get("source_exposed_o0_cell_key"),
            "source_baseline_cell_key": cell.get("source_baseline_cell_key"),
            "unused_target_tool": cell.get("unused_target_tool"),
            "business_rule_intent": cell.get("business_rule_intent"),
            "semantic_class": cell.get("semantic_class"),
            "schema_changed": cell.get("schema_changed"),
            "typed_client_compatible": cell.get("typed_client_compatible"),
        }
    )
    return status


def _run_live_cell(cell: dict[str, Any], log_path: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    provider = str(cell.get("provider") or "")
    key_envs = PROVIDER_KEY_ENV.get(provider, ())
    env = _provider_env()
    if key_envs and not any(env.get(key_env) for key_env in key_envs):
        status = _base_status(cell)
        status.update(
            {
                "status": "provider_error",
                "error_message": f"{' or '.join(key_envs)} is not set; cell not executed",
                "elapsed_s": 0.0,
            }
        )
        return status, None

    with tempfile.TemporaryDirectory(prefix="phase5_cell_") as tmp:
        out_path = Path(tmp) / "batch_cell.jsonl"
        cmd = _batch_command(cell, out_path)
        t0 = time.time()
        proc = subprocess.Popen(
            cmd,
            cwd=str(_REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        timeout = int(cell.get("timeout_seconds", 600)) + 30
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                proc.kill()
            stdout, stderr = proc.communicate()
            status = _base_status(cell)
            status.update(
                {
                    "status": "timeout",
                    "timeout": True,
                    "error_message": f"phase5 subprocess timeout after {timeout}s",
                    "elapsed_s": round(time.time() - t0, 2),
                }
            )
            _append_log(log_path, cell, cmd, stdout, stderr)
            return status, None

        _append_log(log_path, cell, cmd, stdout, stderr)
        records = _read_jsonl(out_path) if out_path.exists() else []
        record = records[-1] if records else {
            "status": "error",
            "error": (stderr or stdout or f"batch_runner exited {proc.returncode}")[:4000],
            "error_type": "BatchRunnerNoRecord",
        }
        status = _convert_batch_record(cell, record)
        if proc.returncode != 0 and status["status"] == "ok":
            status["status"] = "failed"
            status["error_message"] = f"batch_runner exited {proc.returncode}"
        status["elapsed_s"] = status.get("elapsed_s") or round(time.time() - t0, 2)
        return status, record


def _append_log(path: Path, cell: dict[str, Any], cmd: list[str], stdout: str, stderr: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n=== {cell.get('cell_key')} {time.strftime('%Y-%m-%dT%H:%M:%S')} ===\n")
        f.write("CMD " + " ".join(cmd) + "\n")
        if stdout:
            f.write("--- stdout ---\n")
            f.write(stdout[-8000:] + "\n")
        if stderr:
            f.write("--- stderr ---\n")
            f.write(stderr[-8000:] + "\n")


def run_cell(cell: dict[str, Any], log_path: Path, retry: int) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if cell.get("execution_mode") == "local_fake":
        return _fake_status(cell), {"fake": True, "cell": cell}

    last_status: dict[str, Any] | None = None
    last_raw: dict[str, Any] | None = None
    for attempt in range(retry + 1):
        try:
            status, raw = _run_live_cell(cell, log_path)
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc(limit=8)
            status = _base_status(cell)
            text = f"{type(exc).__name__}: {exc}\n{tb}"
            status.update(
                {
                    "status": _classify_error(text),
                    "error_message": text[:4000],
                    "elapsed_s": None,
                }
            )
            raw = None
        status["attempt"] = attempt
        last_status, last_raw = status, raw
        if status["status"] == "ok":
            break
        if attempt < retry:
            time.sleep(min(5, 1 + attempt))
    assert last_status is not None
    return last_status, last_raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--retry", type=int, default=0)
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    shard_path = Path(args.shard)
    if not shard_path.is_absolute():
        shard_path = _REPO_ROOT / shard_path
    cells = _read_jsonl(shard_path)
    shard_name = shard_path.stem
    status_path = STATUS_DIR / f"{shard_name}_status.jsonl"
    raw_path = RAW_DIR / f"{shard_name}_raw.jsonl"
    log_path = LOG_DIR / f"{shard_name}.log"

    print(f"[phase5-shard] shard={shard_path}")
    print(f"[phase5-shard] cells={len(cells)} dry_run={args.dry_run} max_workers={args.max_workers}")
    print(f"[phase5-shard] status={status_path}")
    print(f"[phase5-shard] raw={raw_path}")
    if args.dry_run:
        for cell in cells:
            print(
                "PLAN "
                f"{cell.get('cell_key')} env={cell.get('env')} model={cell.get('model')} "
                f"task={cell.get('task_id')} seed={cell.get('seed')} condition={cell.get('condition')} "
                f"mutation={cell.get('mutation_name') or 'baseline'} mode={cell.get('execution_mode')}"
            )
        return 0

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    status_lock = threading.Lock()
    raw_lock = threading.Lock()
    existing = _terminal_existing(status_path) if args.skip_existing else set()

    planned = []
    for cell in cells:
        if str(cell.get("cell_key")) in existing:
            skipped = _base_status(cell)
            skipped.update({"status": "skipped", "error_message": "existing terminal status", "elapsed_s": 0.0})
            _append_jsonl(status_path, skipped, status_lock)
            print(f"SKIP {cell.get('cell_key')}")
        else:
            planned.append(cell)

    ok = failed = skipped_n = 0

    def _work(cell: dict[str, Any]) -> dict[str, Any]:
        status, raw = run_cell(cell, log_path, args.retry)
        envelope = {"cell_key": cell.get("cell_key"), "cell": cell, "status": status, "raw": raw}
        _append_jsonl(raw_path, envelope, raw_lock)
        _append_jsonl(status_path, status, status_lock)
        return status

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        futures = [pool.submit(_work, cell) for cell in planned]
        for fut in concurrent.futures.as_completed(futures):
            status = fut.result()
            if status["status"] == "ok":
                ok += 1
            elif status["status"] == "skipped":
                skipped_n += 1
            else:
                failed += 1
            print(
                f"{status['status'].upper()} {status.get('cell_key')} "
                f"reward={status.get('reward')} err={str(status.get('error_message') or '')[:100]}"
            )

    print(f"[done] ok={ok} failed={failed} skipped={skipped_n} status={status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
