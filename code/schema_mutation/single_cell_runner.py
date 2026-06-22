"""Run one schema-mutation cell in an isolated subprocess.

Used by batch_runner.py to enforce per-cell timeouts. The parent process writes a
small JSON payload; this module runs runner.run() and writes raw result JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from code.schema_mutation.runner import run as run_one  # noqa: E402


DEFAULT_CFG = {
    "env": "retail",
    "user_strategy": "llm",
    "user_model": "dashscope/qwen-flash",
    "task_split": "test",
    "user_provider": "dashscope",
}


def _make_input(task_index: int, env_name: str) -> dict[str, dict[str, Any]]:
    cfg = dict(DEFAULT_CFG)
    cfg["env"] = env_name
    cfg["task_index"] = task_index
    return {str(task_index): cfg}


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m code.schema_mutation.single_cell_runner <payload.json> <result.json>")
    payload_path = Path(sys.argv[1])
    result_path = Path(sys.argv[2])
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    raw = run_one(
        _make_input(int(payload["task_index"]), str(payload.get("env", "retail"))),
        **(payload.get("run_kwargs") or {}),
    )
    result_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
