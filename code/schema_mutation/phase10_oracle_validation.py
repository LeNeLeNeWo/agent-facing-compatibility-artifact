"""Generate Phase 10A oracle validation packets from persisted artifacts.

This script does not run models. It samples existing baseline, O0, and recovered
records to make the deterministic oracle auditable by humans. The consistency
checks are proxy checks over persisted reward/oracle/status fields, not a
replacement for manual annotation.
"""

from __future__ import annotations

import collections
import json
import random
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PHASE5_STATUS = ROOT / "runs" / "schema_mutation" / "phase5" / "status"
OUT_DIR = ROOT / "runs" / "schema_mutation" / "phase10" / "oracle_validation"
FORMAL_MODELS = {
    "deepseek/deepseek-v4-flash",
    "dashscope/qwen-max",
    "dashscope/kimi-k2.6",
    "dashscope/glm-5.1",
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


def latest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get("cell_key") or "")
        if key:
            by_key[key] = row
    return list(by_key.values())


def status_paths() -> list[Path]:
    paths: list[Path] = []
    patterns = [
        "baseline_*_status.jsonl",
        "airline_baseline_nonwyzlab_*_status.jsonl",
        "observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl",
        "airline_observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl",
        "c_semantic_generalization_[0-9][0-9][0-9][0-9]_status.jsonl",
    ]
    for pattern in patterns:
        paths.extend(PHASE5_STATUS.glob(pattern))
    return sorted(paths)


def load_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in status_paths():
        if "smoke" in path.name or "retry" in path.name:
            continue
        for row in read_jsonl(path):
            row = dict(row)
            row["_source_artifact"] = str(path.relative_to(ROOT))
            rows.append(row)
    rows = latest(rows)
    return [
        r for r in rows
        if r.get("status") == "ok"
        and r.get("fake_run") is not True
        and str(r.get("provider") or "").lower() not in {"wyzlab", "wyzai"}
        and r.get("model") in FORMAL_MODELS
    ]


def reward(row: dict[str, Any]) -> float | None:
    value = row.get("reward", row.get("final_reward"))
    try:
        return float(value)
    except Exception:
        return None


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
    return "baseline"


def category(row: dict[str, Any]) -> str | None:
    mutation = row.get("mutation_name")
    level = row.get("observability_level")
    hidden = bool(row.get("hidden_business_rule_violation"))
    if not mutation or str(row.get("condition")) == "baseline":
        if row.get("baseline_success") is True or reward(row) == 1.0:
            return "baseline_success_unmutated"
    if level == "O0_silent" and hidden:
        return "o0_hidden_violation_positive"
    if level == "O0_silent" and not hidden:
        return "o0_non_hidden_violation_negative"
    if level in {"O3_structured_policy_error", "O4_migration_note"} and reward(row) == 1.0:
        return "o3_o4_recovered"
    return None


def explanation(row: dict[str, Any], cat: str) -> str:
    hidden = bool(row.get("hidden_business_rule_violation"))
    oracle = bool(row.get("oracle_rule_violation"))
    r = reward(row)
    if cat == "baseline_success_unmutated":
        return "Baseline cell succeeded without a semantic mutation; oracle should not fire."
    if cat == "o0_hidden_violation_positive":
        return "O0 silent drift has no visible recovery signal and the hidden rule violation is set."
    if cat == "o0_non_hidden_violation_negative":
        return "O0 cell remained successful or did not hit the changed rule; hidden violation is absent."
    if cat == "o3_o4_recovered":
        return "Visible structured/migration signal is present and the final reward indicates recovery."
    return f"Review oracle={oracle}, hidden={hidden}, reward={r}."


def sample_balanced(rows: list[dict[str, Any]], n: int, seed: int = 1007) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    by_key: dict[tuple[str, str, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        by_key[(str(row.get("env")), str(row.get("model")), semantic_class(row))].append(row)
    sampled: list[dict[str, Any]] = []
    keys = sorted(by_key)
    while len(sampled) < n and keys:
        progressed = False
        for key in list(keys):
            bucket = by_key[key]
            if not bucket:
                keys.remove(key)
                continue
            rng.shuffle(bucket)
            sampled.append(bucket.pop())
            progressed = True
            if len(sampled) >= n:
                break
        if not progressed:
            break
    return sampled


def make_packet() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = load_rows()
    buckets: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        cat = category(row)
        if cat:
            buckets[cat].append(row)
    targets = {
        "baseline_success_unmutated": 50,
        "o0_hidden_violation_positive": 50,
        "o0_non_hidden_violation_negative": 50,
        "o3_o4_recovered": 30,
    }
    packet: list[dict[str, Any]] = []
    for cat, target in targets.items():
        for row in sample_balanced(buckets.get(cat, []), target):
            packet.append(to_packet_row(row, cat))
    suspicious = [r for r in packet if r["suspicious"]]
    baseline = [r for r in packet if r["sample_category"] == "baseline_success_unmutated"]
    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_samples": len(packet),
        "sample_counts": dict(collections.Counter(r["sample_category"] for r in packet)),
        "by_env": dict(collections.Counter(r["env"] for r in packet)),
        "by_model": dict(collections.Counter(r["model"] for r in packet)),
        "by_semantic_class": dict(collections.Counter(r["semantic_class"] for r in packet)),
        "baseline_oracle_violation_rate": (
            sum(1 for r in baseline if r["oracle_rule_violation"]) / len(baseline)
            if baseline else None
        ),
        "o0_positive_consistency": consistency(packet, "o0_hidden_violation_positive"),
        "o0_negative_consistency": consistency(packet, "o0_non_hidden_violation_negative"),
        "recovered_consistency": consistency(packet, "o3_o4_recovered"),
        "suspicious_count": len(suspicious),
        "suspicious_sample_ids": [r["sample_id"] for r in suspicious[:20]],
        "precision_specificity_proxy_note": (
            "Proxy only: baseline/non-hidden samples approximate specificity and "
            "O0 hidden-positive samples approximate rule-trigger consistency. "
            "Human annotation is still required for oracle precision."
        ),
    }
    return packet, summary


def consistency(packet: list[dict[str, Any]], cat: str) -> float | None:
    subset = [r for r in packet if r["sample_category"] == cat]
    if not subset:
        return None
    if cat == "o0_hidden_violation_positive":
        good = [r for r in subset if r["hidden_business_rule_violation"] and r["reward"] == 0.0]
    elif cat == "o0_non_hidden_violation_negative":
        good = [r for r in subset if not r["hidden_business_rule_violation"]]
    elif cat == "o3_o4_recovered":
        good = [r for r in subset if r["reward"] == 1.0 and not r["hidden_business_rule_violation"]]
    else:
        good = [r for r in subset if not r["oracle_rule_violation"]]
    return len(good) / len(subset)


def to_packet_row(row: dict[str, Any], cat: str) -> dict[str, Any]:
    r = reward(row)
    hidden = bool(row.get("hidden_business_rule_violation"))
    oracle = bool(row.get("oracle_rule_violation"))
    suspicious = False
    if cat == "baseline_success_unmutated" and oracle:
        suspicious = True
    if cat == "o0_hidden_violation_positive" and (not hidden or r != 0.0):
        suspicious = True
    if cat == "o0_non_hidden_violation_negative" and hidden:
        suspicious = True
    if cat == "o3_o4_recovered" and (hidden or r != 1.0):
        suspicious = True
    return {
        "sample_id": f"oracle_{cat}_{row.get('cell_key')}",
        "sample_category": cat,
        "cell_key": row.get("cell_key"),
        "source_artifact": row.get("_source_artifact"),
        "env": row.get("env"),
        "model": row.get("model"),
        "provider": row.get("provider"),
        "task_id": row.get("task_id"),
        "seed": row.get("seed"),
        "condition": row.get("condition"),
        "observability_level": row.get("observability_level"),
        "mutation_name": row.get("mutation_name"),
        "semantic_class": semantic_class(row),
        "target_tool": row.get("target_tool"),
        "tool_call_summary": f"target_tool={row.get('target_tool')}; target_tool_called={row.get('target_tool_called')}",
        "relevant_final_state": f"reward={r}; failure_mode={row.get('failure_mode')}",
        "oracle_rule_violation": oracle,
        "hidden_business_rule_violation": hidden,
        "visible_policy_error": bool(row.get("visible_policy_error")),
        "structured_policy_error_visible": bool(row.get("structured_policy_error_visible")),
        "migration_note_visible": bool(row.get("migration_note_visible")),
        "reward": r,
        "mutation_rule": row.get("business_rule_intent") or row.get("mutation_name"),
        "oracle_explanation": explanation(row, cat),
        "raw_trace_pointer": row.get("_source_artifact"),
        "suspicious": suspicious,
    }


def write_outputs(packet: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT_DIR / "oracle_validation_packet.jsonl", packet)
    (OUT_DIR / "oracle_validation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    lines = [
        "# Phase 10A Oracle Validation Summary",
        "",
        "This packet is human-review-ready. It does not claim human-validated oracle precision.",
        "",
        f"- Total samples: {summary['total_samples']}",
        f"- Sample counts: {summary['sample_counts']}",
        f"- By env: {summary['by_env']}",
        f"- By model: {summary['by_model']}",
        f"- By semantic class: {summary['by_semantic_class']}",
        f"- Baseline oracle violation rate: {summary['baseline_oracle_violation_rate']}",
        f"- O0 positive consistency: {summary['o0_positive_consistency']}",
        f"- O0 negative consistency: {summary['o0_negative_consistency']}",
        f"- Recovered consistency: {summary['recovered_consistency']}",
        f"- Suspicious samples: {summary['suspicious_count']}",
        "",
        "## Suspicious Samples for Human Review",
    ]
    for sample_id in summary["suspicious_sample_ids"]:
        lines.append(f"- {sample_id}")
    lines += ["", f"Note: {summary['precision_specificity_proxy_note']}"]
    (OUT_DIR / "oracle_validation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    packet_lines = [
        "# Phase 10A Oracle Validation Packet",
        "",
        "See `oracle_validation_packet.jsonl` for per-cell details.",
        "",
        "Review fields include cell key, source artifact, tool summary, final reward, oracle flags, mutation rule, and explanation.",
    ]
    (OUT_DIR / "oracle_validation_packet.md").write_text("\n".join(packet_lines) + "\n", encoding="utf-8")


def main() -> int:
    packet, summary = make_packet()
    write_outputs(packet, summary)
    print(f"samples={len(packet)} suspicious={summary['suspicious_count']} out={OUT_DIR}")
    return 0 if len(packet) >= 150 else 2


if __name__ == "__main__":
    raise SystemExit(main())
