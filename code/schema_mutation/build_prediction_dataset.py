"""Build a deconfounded prediction dataset for agent-facing breakage.

The main dataset only includes paired baseline-successful mutation cells, or
gate records that contain replay evidence. Final success/failure labels are
stored for evaluation but are not predictor features.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from code.schema_mutation.c4_observability_modes import normalize_observability_level  # noqa: E402
from code.schema_mutation.mutator import ATTRIBUTE_MATRIX  # noqa: E402

RUNS = _REPO_ROOT / "runs" / "schema_mutation"

DEFAULT_ARTIFACTS = [
    RUNS / "paired_multimutation_labeled.jsonl",
    RUNS / "paired_multimutation_analysis.jsonl",
    RUNS / "paired_c4_runtime_fixed_labeled.jsonl",
    RUNS / "paired_day10_c4a_c4b_deepseek.jsonl",
    RUNS / "paired_day11_c4a_c4b_qwen_kimi.jsonl",
    RUNS / "paired_day16_airline_deepseek_s0_unused_control.jsonl",
    RUNS / "paired_day16_airline_deepseek_s12_c4a_c4b.jsonl",
    RUNS / "paired_day16_airline_qwen_max_c4a_c4b.jsonl",
    RUNS / "gate_evaluation_records.jsonl",
]

PHASE5_OBSERVABILITY_PATTERNS = [
    "phase5/status/observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl",
    "phase5/status/airline_observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl",
]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
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


def _infer_env(path: Path, row: dict[str, Any]) -> str:
    if row.get("env"):
        return str(row["env"])
    return "airline" if "airline" in path.name.lower() else "retail"


def _mutation_name(row: dict[str, Any]) -> str:
    return str(row.get("mutation_type_v2") or row.get("mutation_type") or row.get("mutation") or "unknown")


def _attrs(mutation: str, row: dict[str, Any]) -> dict[str, str]:
    attrs = row.get("attrs")
    if isinstance(attrs, dict):
        return {str(k): str(v) for k, v in attrs.items()}
    return ATTRIBUTE_MATRIX.get(mutation, {})


def _safe_observability(row: dict[str, Any]) -> str:
    raw = row.get("observability_level") or row.get("c4_runtime_mode")
    if raw:
        try:
            return normalize_observability_level(str(raw))
        except Exception:
            pass
    mode = str(row.get("runtime_policy_mode") or row.get("oracle_rule_mode") or "")
    if mode:
        try:
            return normalize_observability_level(None, mode)
        except Exception:
            pass
    return "unknown"


def _bool_y(value: Any) -> bool:
    return str(value).upper() == "Y"


def _target_policy_type(value: Any) -> str:
    policy = str(value or "unknown")
    if policy.startswith("unused"):
        return "unused"
    if "intent" in policy:
        return "intent_aligned"
    if policy in {"used_tool", "random", "unknown"}:
        return policy
    return "other"


def _tool_family(tool: Any) -> str:
    s = str(tool or "unknown")
    for key in (
        "exchange", "return", "cancel", "modify", "payment", "address", "order",
        "product", "user", "book", "reservation", "flight", "baggage", "passenger",
    ):
        if key in s:
            return key
    return s.split("_")[0] if s else "unknown"


def _from_gate_record(row: dict[str, Any], path: Path) -> dict[str, Any] | None:
    if row.get("agent_mutation_success") is None:
        return None
    converted = {
        "env": row.get("env"),
        "model": row.get("model"),
        "task_index": row.get("task_id"),
        "seed": row.get("seed"),
        "mutation_type": row.get("mutation"),
        "target_policy": "intent_aligned" if row.get("exposure_level") == "intent_aligned" else row.get("exposure_level"),
        "c4_runtime_mode": row.get("c4_runtime_mode"),
        "observability_level": row.get("observability_level"),
        "baseline_reward": 1.0 if row.get("agent_baseline_success") else 0.0,
        "mutation_reward": 1.0 if row.get("agent_mutation_success") else 0.0,
        "mutation_tool": row.get("target_tool"),
        "oracle_rule_violation": row.get("semantic_oracle_pass") is False,
        "visible_policy_error": row.get("observability_signal") in {"policy_error", "generic_error", "structured_policy_error", "migration_note"},
        "generic_error_visible": row.get("observability_signal") == "generic_error",
        "structured_policy_error_visible": row.get("observability_signal") == "structured_policy_error",
        "migration_note_visible": row.get("observability_signal") == "migration_note",
        "hidden_business_rule_violation": row.get("eval_silent_regression_label"),
        "failure_mode": row.get("failure_mode"),
        "source_gate_method": row.get("method_display"),
        "_source_artifact_override": row.get("source"),
    }
    return converted


def _from_phase5_status(row: dict[str, Any], path: Path) -> dict[str, Any] | None:
    """Convert final Phase 5 status rows into paired baseline/mutation evidence.

    Prediction labels use the cached mutation result. Provider errors, timeouts,
    fake/smoke rows, WYZ partial experiments, and baseline-unsuccessful rows are
    excluded before conversion.
    """
    source = path.name.lower()
    if "smoke" in source or "retry_provider_error" in source:
        return None
    if row.get("fake_run"):
        return None
    if row.get("status") != "ok" or row.get("timeout"):
        return None
    if row.get("provider") == "wyzlab" or "wyzlab" in str(row.get("model", "")).lower():
        return None
    if row.get("baseline_success") is not True:
        return None
    if row.get("observability_level") not in {
        "O0_silent", "O1_generic_error", "O2_policy_error", "O3_structured_policy_error", "O4_migration_note",
    }:
        return None
    return {
        "env": row.get("env"),
        "model": row.get("model"),
        "task_id": row.get("task_id"),
        "seed": row.get("seed"),
        "mutation_type": row.get("mutation_name") or "C4_business_rule_drift",
        "target_policy": row.get("protocol") or "intent_aligned",
        "observability_level": row.get("observability_level"),
        "c4_runtime_mode": row.get("condition"),
        "baseline_reward": 1.0,
        "mutation_reward": float(row.get("reward") or 0.0),
        "mutation_tool": row.get("target_tool") or "unknown",
        "target_tool": row.get("target_tool") or "unknown",
        "oracle_rule_violation": row.get("oracle_rule_violation"),
        "visible_policy_error": row.get("visible_policy_error"),
        "generic_error_visible": row.get("generic_error_visible"),
        "structured_policy_error_visible": row.get("structured_policy_error_visible"),
        "migration_note_visible": row.get("migration_note_visible"),
        "hidden_business_rule_violation": row.get("hidden_business_rule_violation"),
        "failure_mode": row.get("failure_mode"),
        "intent_aligned": row.get("protocol") == "intent_aligned",
        "runtime_policy_action": row.get("target_tool") if row.get("target_tool_called") else None,
        "oracle_rule_action": row.get("target_tool") if row.get("target_tool_called") else None,
        "mutation_num_actions": row.get("num_actions"),
        "baseline_num_actions": 0,
        "_source_artifact_override": str(path),
        "_phase5_cell_key": row.get("cell_key"),
    }


def _is_phase5_status_path(path: Path) -> bool:
    name = path.name
    return path.parent.name == "status" and "observability_from_baseline" in name


def _latest_by_cell_key(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Keep the latest Phase 5 status row per cell_key.

    Some airline runs include an initial provider_error row followed by a
    successful retry in the same status file. We use cached status rows only as
    evaluation metadata, so deduplicating by cell_key avoids counting retry
    attempts as separate agent-facing outcomes.
    """

    latest: dict[str, tuple[tuple[str, int], dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        key = row.get("cell_key")
        if not key:
            passthrough.append(row)
            continue
        time_key = str(row.get("started_at") or row.get("completed_at") or row.get("timestamp") or "")
        order_key = (time_key, idx)
        if key not in latest or order_key >= latest[key][0]:
            latest[key] = (order_key, row)
    deduped = passthrough + [item[1] for item in latest.values()]
    return deduped, max(0, len(rows) - len(deduped))


def row_to_sample(row: dict[str, Any], path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if _is_phase5_status_path(path):
        row = _from_phase5_status(row, path) or {}
        if not row:
            return None, "phase5_status_not_formal"
    if path.name == "gate_evaluation_records.jsonl":
        row = _from_gate_record(row, path) or {}
        if not row:
            return None, "gate_record_without_replay_evidence"
    if row.get("fake_run"):
        return None, "fake_run"
    if "baseline_reward" not in row or "mutation_reward" not in row:
        return None, "not_paired_baseline_mutation"
    baseline_success = float(row.get("baseline_reward") or 0.0) > 0
    if not baseline_success:
        return None, "baseline_not_successful"

    mutation = _mutation_name(row)
    attrs = _attrs(mutation, row)
    env = _infer_env(path, row)
    task_id = str(row.get("task_id", row.get("task_index", "unknown")))
    seed = int(row.get("seed") or 0)
    model = str(row.get("model") or "unknown")
    target_tool = row.get("target_tool") or row.get("mutation_tool") or "unknown"
    target_policy = str(row.get("target_policy") or "unknown")
    obs = _safe_observability(row)

    mutation_success = float(row.get("mutation_reward") or row.get("final_reward") or 0.0) > 0
    agent_breaking = baseline_success and not mutation_success
    oracle_violation = bool(row.get("oracle_rule_violation") or row.get("runtime_policy_violation"))
    hidden_violation = bool(row.get("hidden_business_rule_violation"))
    visible_error = bool(row.get("visible_policy_error")) or obs in {
        "O1_generic_error", "O2_policy_error", "O3_structured_policy_error", "O4_migration_note",
    }
    generic_error = bool(row.get("generic_error_visible")) or obs == "O1_generic_error"
    structured_error = bool(row.get("structured_policy_error_visible")) or obs == "O3_structured_policy_error"
    migration_note = bool(row.get("migration_note_visible")) or obs == "O4_migration_note"
    silent = obs == "O0_silent" or str(row.get("c4_runtime_mode") or "") in {"silent", "C4b", "silent_business_rule_drift"}

    policy_type = _target_policy_type(target_policy)
    intent_aligned = bool(row.get("intent_aligned")) or policy_type == "intent_aligned"
    target_tool_called = bool(
        row.get("oracle_rule_action")
        or row.get("runtime_policy_action")
        or (policy_type in {"intent_aligned", "used_tool"} and target_tool != "unknown")
    )
    if policy_type == "unused":
        target_tool_called = False

    baseline_calls = int(row.get("baseline_num_actions") or row.get("baseline_num_tool_calls") or 0)
    mutation_calls = int(row.get("mutation_num_actions") or 0)
    tool_pos = 0.5 if target_tool_called and baseline_calls else -1.0
    tool_freq = (1.0 / baseline_calls) if target_tool_called and baseline_calls else 0.0
    mutation_class = mutation[:1] if mutation[:1] in {"A", "B", "C", "D"} else "unknown"
    semantic_change = _bool_y(attrs.get("semantics_changing"))
    schema_visible = _bool_y(attrs.get("schema_visible"))
    trad = str(attrs.get("traditional_compatible", "?"))

    sample_id = (
        _sample_id("phase5", row.get("_phase5_cell_key"))
        if row.get("_phase5_cell_key")
        else _sample_id(env, model, task_id, seed, mutation, target_tool, target_policy, obs)
    )
    sample = {
        "sample_id": sample_id,
        "source_artifact": str(row.get("_source_artifact_override") or path),
        "env": env,
        "model": model,
        "task_id": task_id,
        "seed": seed,
        "mutation_class": mutation_class,
        "mutation_name": mutation,
        "observability_level": obs,
        "target_tool": target_tool,
        "target_policy": target_policy,
        "target_policy_type": policy_type,
        "tool_family": _tool_family(target_tool),
        "schema_visible": schema_visible,
        "semantic_change": semantic_change,
        "traditional_label": trad,
        "schema_client_compatible": trad == "Y",
        "endpoint_changed": False,
        "param_rename": mutation in {"A1_identifier_rename", "A2_format_change", "M01_rename"},
        "type_changed": mutation in {"B1_type_change", "M02_type_change"},
        "requiredness_changed": mutation in {"B2_requiredness_change", "M03_requiredness_change"},
        "enum_changed": mutation in {"B3_enum_change", "M06_enum_rename"},
        "output_shape_changed": mutation == "B4_output_schema_change",
        "unit_scale": mutation == "C1_unit_scale_drift",
        "currency_locale": mutation == "C2_currency_locale_drift",
        "default_behavior": mutation == "C3_default_behavior_drift",
        "business_rule": mutation == "C4_business_rule_drift",
        "protocol_change": mutation.startswith("D"),
        "target_tool_called": target_tool_called,
        "target_param_used": False,
        "target_response_observed": False,
        "intent_aligned": intent_aligned,
        "field_state_exposed": bool(target_tool_called or intent_aligned),
        "reward_critical": bool((target_tool_called or intent_aligned) and semantic_change),
        "reward_critical_prior": bool((target_tool_called or intent_aligned) and semantic_change),
        "visible_error": visible_error,
        "generic_error": generic_error,
        "structured_error": structured_error,
        "migration_note": migration_note,
        "silent": silent,
        "baseline_num_tool_calls": baseline_calls,
        "baseline_num_retries": max(0, mutation_calls - baseline_calls) if mutation_calls and baseline_calls else 0,
        "baseline_trajectory_length": baseline_calls,
        "tool_call_position": tool_pos,
        "tool_call_frequency": tool_freq,
        "baseline_success": baseline_success,
        "mutation_success": mutation_success,
        "agent_breaking": agent_breaking,
        "failure_mode": row.get("failure_mode") or ("agent_compatible" if not agent_breaking else "unknown_failure"),
        "oracle_rule_violation": oracle_violation,
        "hidden_business_rule_violation": hidden_violation,
    }
    sample["negative_type"] = _negative_type(sample)
    sample["positive_type"] = _positive_type(sample)
    return sample, None


def _negative_type(sample: dict[str, Any]) -> str | None:
    if sample["agent_breaking"]:
        return None
    if sample["target_policy_type"] == "unused" or not sample["target_tool_called"]:
        return "easy_negative"
    if (
        sample["schema_visible"]
        or sample["semantic_change"]
        or sample["visible_error"]
        or sample["oracle_rule_violation"]
        or sample["business_rule"]
    ):
        return "hard_negative"
    return "easy_negative"


def _positive_type(sample: dict[str, Any]) -> str | None:
    if not sample["agent_breaking"]:
        return None
    if sample["silent"] and sample["business_rule"]:
        return "exposed_c4b_silent_breaking"
    if sample["semantic_change"] and sample["schema_client_compatible"]:
        return "schema_compatible_semantic_breaking"
    return "agent_breaking"


def _sample_id(*parts: Any) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _discover_artifacts() -> list[Path]:
    candidates = list(DEFAULT_ARTIFACTS)
    candidates.extend(sorted((RUNS / "split_day6").glob("*.jsonl")))
    candidates.extend(sorted(RUNS.glob("*observability*.jsonl")))
    return _dedup_paths(candidates)


def _phase5_observability_artifacts() -> list[Path]:
    paths: list[Path] = []
    for pattern in PHASE5_OBSERVABILITY_PATTERNS:
        paths.extend(sorted(RUNS.glob(pattern)))
    return _dedup_paths(paths)


def _dedup_paths(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen = set()
    for p in paths:
        key = str(p.resolve()) if p.exists() else str(p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _summary(samples: list[dict[str, Any]], skipped: collections.Counter, artifact_rows: dict[str, int]) -> dict[str, Any]:
    def counter(field: str) -> dict[str, int]:
        return dict(collections.Counter(str(s.get(field, "unknown")) for s in samples))

    total = len(samples)
    missing_fields = {}
    required = [
        "env", "model", "task_id", "mutation_name", "observability_level", "target_tool",
        "target_policy", "failure_mode",
    ]
    for field in required:
        missing_fields[field] = sum(1 for s in samples if s.get(field) in {None, "", "unknown"}) / max(total, 1)
    positives = sum(1 for s in samples if s["agent_breaking"])
    hard_negatives = sum(1 for s in samples if s.get("negative_type") == "hard_negative")
    easy_negatives = sum(1 for s in samples if s.get("negative_type") == "easy_negative")
    warnings = []
    if hard_negatives < max(10, total * 0.1):
        warnings.append("hard negatives are sparse; run more exposed-but-recoverable A/C semantic and O3/O4 cells")
    if counter("mutation_class").get("C", 0) > total * 0.8:
        warnings.append("dataset is C-class heavy; add more paired A/B/D mutation runs for predictor generalization")
    phase5_samples = sum(1 for s in samples if "phase5/status" in str(s.get("source_artifact", "")).replace("\\", "/"))
    return {
        "total_samples": total,
        "positives": positives,
        "negatives": total - positives,
        "hard_negatives": hard_negatives,
        "easy_negatives": easy_negatives,
        "by_env": counter("env"),
        "by_model": counter("model"),
        "by_mutation_class": counter("mutation_class"),
        "by_observability_level": counter("observability_level"),
        "by_target_tool": counter("target_tool"),
        "by_negative_type": counter("negative_type"),
        "by_positive_type": counter("positive_type"),
        "missing_field_rates": missing_fields,
        "artifact_rows": artifact_rows,
        "phase5_observability_included": phase5_samples > 0,
        "phase5_observability_samples": phase5_samples,
        "skipped": dict(skipped),
        "warnings": warnings,
    }


def _write_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Predictor Dataset Summary",
        "",
        f"Total samples: {summary['total_samples']}",
        f"Positives: {summary['positives']}",
        f"Negatives: {summary['negatives']}",
        f"Hard negatives: {summary['hard_negatives']}",
        f"Easy negatives: {summary['easy_negatives']}",
        f"Phase 5 observability included: {summary.get('phase5_observability_included')}",
        f"Phase 5 observability samples: {summary.get('phase5_observability_samples')}",
        "",
        "Warnings:",
    ]
    lines.extend(f"- {w}" for w in summary["warnings"] or ["none"])
    lines.extend(["", "Skipped rows:"])
    lines.extend(f"- {k}: {v}" for k, v in sorted(summary["skipped"].items()))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(inputs: list[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    samples_by_id: dict[str, dict[str, Any]] = {}
    skipped: collections.Counter = collections.Counter()
    artifact_rows: dict[str, int] = {}
    for path in inputs:
        rows = _read_jsonl(path)
        artifact_rows[str(path)] = len(rows)
        if not rows:
            skipped["missing_or_empty_artifact"] += 1
            continue
        if _is_phase5_status_path(path):
            rows, duplicate_count = _latest_by_cell_key(rows)
            if duplicate_count:
                skipped["phase5_duplicate_status_row"] += duplicate_count
        for row in rows:
            sample, reason = row_to_sample(row, path)
            if sample is None:
                skipped[reason or "unknown_skip"] += 1
                continue
            if sample["sample_id"] in samples_by_id:
                skipped["duplicate_sample"] += 1
                continue
            samples_by_id[sample["sample_id"]] = sample
    samples = list(samples_by_id.values())
    samples.sort(key=lambda s: (s["env"], s["model"], s["task_id"], s["seed"], s["mutation_name"], s["observability_level"]))
    return samples, _summary(samples, skipped, artifact_rows)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("inputs", nargs="*")
    p.add_argument("--input-existing-artifacts", action="store_true")
    p.add_argument("--include-phase5-observability", action="store_true")
    p.add_argument("--inspect-artifacts", action="store_true")
    p.add_argument("--overwrite", action="store_true", help="accepted for workflow symmetry; output files are overwritten")
    p.add_argument("--out", default="runs/schema_mutation/predictor_dataset.jsonl")
    p.add_argument("--summary-out", default="runs/schema_mutation/predictor_dataset_summary.json")
    args = p.parse_args()

    if args.inputs:
        inputs = [Path(x) if Path(x).is_absolute() else _REPO_ROOT / x for x in args.inputs]
    else:
        inputs = _discover_artifacts()
    if args.include_phase5_observability:
        # Gate records are evaluator outputs and may have just been regenerated
        # from the same Phase 5 status rows. In Phase 5 mode, use formal status
        # rows as the primary source and avoid feeding gate outputs back into
        # the predictor dataset.
        if not args.inputs:
            inputs = [p for p in inputs if p.name != "gate_evaluation_records.jsonl"]
        inputs = _dedup_paths(inputs + _phase5_observability_artifacts())

    if args.inspect_artifacts:
        print("[predictor-dataset] inspect")
        for path in inputs:
            rows = _read_jsonl(path)
            paired = sum(1 for r in rows if "baseline_reward" in r and "mutation_reward" in r)
            print(f"{path}\trows={len(rows)}\tpaired_like={paired}")
        return 0

    samples, summary = build(inputs)
    out = Path(args.out)
    if not out.is_absolute():
        out = _REPO_ROOT / out
    summary_out = Path(args.summary_out)
    if not summary_out.is_absolute():
        summary_out = _REPO_ROOT / summary_out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_md(summary_out.with_suffix(".md"), summary)
    print(f"samples={len(samples)} positives={summary['positives']} hard_negatives={summary['hard_negatives']}")
    for warning in summary["warnings"]:
        print(f"[warn] {warning}")
    print(f"dataset={out}")
    print(f"summary={summary_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
