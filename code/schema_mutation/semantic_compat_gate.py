"""Prototype Agent-Facing Compatibility Gate (AFC-Gate).

The gate consumes baseline-successful trajectories plus candidate evolved API
evidence. In this prototype, existing paired JSONL artifacts can stand in for
actual replay execution. The distinction is explicit:

- prediction features: static schema/client compatibility, exposure metadata,
  mutation metadata, observability metadata.
- gate execution evidence: semantic oracle result and mutation trajectory only
  for cells selected by a replay method.
- evaluation labels: final agent success/failure, used only by evaluate_gate.py.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from code.schema_mutation.gate_policies import (
    GATE_METHODS,
    afc_decision,
    classify_static_compat,
    exposure_level,
    observability_signal,
)


@dataclass(frozen=True)
class GateConfig:
    method: str = "AFCGate"
    replay_budget: int | None = 10
    seed: int = 7


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    rows: list[dict[str, Any]] = []
    if not p.exists():
        return rows
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def is_budget_all(value: str | int | None) -> bool:
    return str(value or "").lower() == "all"


def parse_budget(value: str | int | None) -> int | None:
    if value is None or is_budget_all(value):
        return None
    return int(value)


def normalize_cell(row: dict[str, Any], source: str = "") -> dict[str, Any]:
    mutation = row.get("mutation_type") or row.get("mutation")
    target_tool = row.get("target_tool") or row.get("mutation_tool")
    oracle_action = row.get("oracle_rule_action") or row.get("runtime_policy_action")
    policy = row.get("target_policy", "random")
    obs = observability_signal(row)
    static = classify_static_compat(str(mutation) if mutation else None)
    baseline_success = float(row.get("baseline_reward", 0.0) or 0.0) > 0
    mutation_success = float(
        row.get("final_reward", row.get("mutation_reward", row.get("reward", 0.0))) or 0.0
    ) > 0
    oracle_violation = bool(
        row.get("semantic_oracle_fails")
        or row.get("oracle_rule_violation")
        or row.get("runtime_policy_violation")
        or row.get("hidden_business_rule_violation")
    )
    exp_level = row.get("exposure_level") or exposure_level(policy, target_tool, oracle_action)
    return {
        "source": source,
        "env": row.get("env", _infer_env_from_source(source)),
        "model": row.get("model"),
        "task_id": str(row.get("task_id", row.get("task_index"))),
        "seed": int(row.get("seed", 0) or 0),
        "mutation": mutation,
        "target_tool": target_tool,
        "target_policy": policy,
        "exposure_level": exp_level,
        "execution_exposed": exp_level not in {"unexposed", "unknown"},
        "schema_checker_pass": static.schema_checker_pass,
        "typed_client_checker_pass": static.typed_client_checker_pass,
        "static_reasons": list(static.reasons),
        "observability_signal": obs,
        "observability_level": row.get("observability_level"),
        "c4_runtime_mode": row.get("c4_runtime_mode"),
        "agent_baseline_success": baseline_success,
        "agent_mutation_success": mutation_success,
        "semantic_oracle_fails_label": oracle_violation,
        "visible_policy_error": bool(row.get("visible_policy_error")),
        "hidden_business_rule_violation": bool(row.get("hidden_business_rule_violation")),
        "failure_mode": row.get("failure_mode"),
        "raw": row,
    }


def _infer_env_from_source(source: str) -> str:
    s = source.lower()
    if "airline" in s:
        return "airline"
    return "retail"


def select_replay_indices(cells: list[dict[str, Any]], config: GateConfig) -> set[int]:
    if config.method in {"SchemaCheckerOnly"}:
        return set()
    if config.method == "ExhaustiveReplayOracle" or config.replay_budget is None:
        return set(range(len(cells)))

    candidates = list(range(len(cells)))
    if config.method == "UsedToolReplayGate":
        candidates = [i for i, c in enumerate(cells) if c["exposure_level"] in {"used_tool", "intent_aligned", "executed_target_tool"}]
    elif config.method in {"IntentAlignedReplayGate", "AFCGate"}:
        preferred = [i for i, c in enumerate(cells) if c["exposure_level"] == "intent_aligned"]
        fallback = [i for i, c in enumerate(cells) if i not in preferred]
        candidates = preferred + fallback
    elif config.method == "RandomReplayGate":
        candidates = sorted(
            candidates,
            key=lambda i: _stable_hash((cells[i]["env"], cells[i]["model"], cells[i]["task_id"], cells[i]["seed"], config.seed)),
        )
    else:
        raise ValueError(f"unknown gate method: {config.method!r}; valid={GATE_METHODS}")

    return set(candidates[: max(config.replay_budget or 0, 0)])


def _stable_hash(parts: Iterable[Any]) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def run_gate(cells: list[dict[str, Any]], config: GateConfig) -> list[dict[str, Any]]:
    replay_indices = select_replay_indices(cells, config)
    results: list[dict[str, Any]] = []
    for i, cell in enumerate(cells):
        replay_ran = i in replay_indices
        semantic_oracle_pass: bool | None = None
        mutation_success: bool | None = None
        tests_run = 0
        if replay_ran:
            tests_run = 1
            # Gate execution evidence: this comes from a replayed trajectory or
            # an existing paired replay artifact used as a cache.
            semantic_oracle_pass = not bool(cell["semantic_oracle_fails_label"])
            mutation_success = bool(cell["agent_mutation_success"])

        decision, reason = _decide_for_method(cell, config.method, replay_ran, semantic_oracle_pass)
        results.append(
            {
                "gate_method": _method_id(config.method),
                "method_display": config.method,
                "env": cell["env"],
                "model": cell["model"],
                "task_id": cell["task_id"],
                "seed": cell["seed"],
                "mutation": cell["mutation"],
                "target_tool": cell["target_tool"],
                "exposure_level": cell["exposure_level"],
                "schema_checker_pass": cell["schema_checker_pass"],
                "typed_client_checker_pass": cell["typed_client_checker_pass"],
                "semantic_oracle_pass": semantic_oracle_pass,
                "agent_baseline_success": cell["agent_baseline_success"],
                "agent_mutation_success": mutation_success,
                "gate_decision": decision,
                "gate_reason": reason,
                "tests_run": tests_run,
                "estimated_cost": f"{tests_run} replay cell(s)",
                "failure_mode": cell["failure_mode"],
                "observability_signal": cell["observability_signal"],
                "observability_level": cell["observability_level"],
                "c4_runtime_mode": cell["c4_runtime_mode"],
                "source": cell["source"],
                # Evaluation labels are emitted for evaluator transparency; gate
                # policies above do not consume them as prediction features.
                "eval_agent_breakage_label": bool(
                    cell["agent_baseline_success"] and not cell["agent_mutation_success"]
                ),
                "eval_silent_regression_label": bool(
                    cell["agent_baseline_success"]
                    and not cell["agent_mutation_success"]
                    and (
                        cell["hidden_business_rule_violation"]
                        or cell["observability_signal"] == "none"
                    )
                ),
            }
        )
    return results


def _decide_for_method(
    cell: dict[str, Any],
    method: str,
    replay_ran: bool,
    semantic_oracle_pass: bool | None,
) -> tuple[str, str]:
    static_result = classify_static_compat(str(cell["mutation"]) if cell["mutation"] else None)
    if method == "SchemaCheckerOnly":
        if not static_result.schema_checker_pass or not static_result.typed_client_checker_pass:
            return "warn", "static schema/client checker reports a compatibility risk"
        return "pass", "static schema/client checker finds no breaking change"

    if method in {"RandomReplayGate", "UsedToolReplayGate", "IntentAlignedReplayGate", "ExhaustiveReplayOracle"}:
        if not replay_ran:
            return "pass", "cell not selected under replay budget"
        if semantic_oracle_pass is False and not cell["agent_mutation_success"]:
            return "block", "replayed agent trajectory regresses and semantic oracle fails"
        if semantic_oracle_pass is False:
            return "warn", "replayed semantic oracle fails but final agent reward recovers"
        return "pass", "selected replay cell passes semantic oracle"

    if method == "AFCGate":
        return afc_decision(
            static_result=static_result,
            execution_exposed=bool(cell["execution_exposed"]),
            semantic_oracle_pass=semantic_oracle_pass,
            observability=cell["observability_signal"],
            replay_ran=replay_ran,
        )
    raise ValueError(f"unknown gate method: {method!r}")


def _method_id(method: str) -> str:
    return "afc_gate" if method == "AFCGate" else method.lower()
