#!/usr/bin/env python3
"""Build the Phase 5C observability review packet from existing artifacts.

This script is intentionally offline: it only reads Phase 5B status/summary
artifacts and writes review packet files. It does not call providers or run
experiments.
"""

from __future__ import annotations

import json
import math
import random
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PHASE5 = ROOT / "runs" / "schema_mutation" / "phase5"
STATUS_DIR = PHASE5 / "status"
SUMMARY_JSON = PHASE5 / "phase5_summary.json"
SUMMARY_MD = PHASE5 / "phase5_summary.md"
OUT_MD = PHASE5 / "observability_review_packet.md"
OUT_JSON = PHASE5 / "observability_review_packet.json"

LEVELS = [
    "O0_silent",
    "O1_generic_error",
    "O2_policy_error",
    "O3_structured_policy_error",
    "O4_migration_note",
]

CRITICAL_FIELDS = [
    "observability_level",
    "env",
    "model",
    "provider",
    "task_id",
    "seed",
    "reward",
    "baseline_success",
    "visible_policy_error",
    "hidden_business_rule_violation",
    "structured_policy_error_visible",
    "migration_note_visible",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid JSONL in {path}:{line_no}: {exc}") from exc
    return rows


def is_mutation_candidate(row: dict[str, Any]) -> bool:
    for key in ("shard", "source_shard", "input_shard", "source_path", "path"):
        value = row.get(key)
        if isinstance(value, str) and "mutation_candidate" in value:
            return True
    return False


def is_formal_candidate(row: dict[str, Any]) -> bool:
    if row.get("fake_run") is True:
        return False
    if row.get("baseline_success") is not True:
        return False
    if row.get("provider") == "wyzlab":
        return False
    model = str(row.get("model", ""))
    if "wyzlab" in model or "gpt-5.5" in model:
        return False
    if is_mutation_candidate(row):
        return False
    return True


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def is_success(row: dict[str, Any]) -> bool:
    return as_float(row.get("reward")) >= 0.5


def visible_signal(row: dict[str, Any]) -> bool:
    return bool(
        row.get("visible_policy_error")
        or row.get("generic_error_visible")
        or row.get("structured_policy_error_visible")
        or row.get("migration_note_visible")
    )


def wilson_ci(success: int, n: int, z: float = 1.959963984540054) -> list[float | None]:
    if n <= 0:
        return [None, None]
    p = success / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) / n) + (z * z / (4 * n * n))) / denom
    return [max(0.0, center - margin), min(1.0, center + margin)]


def bootstrap_diff_ci(
    a_values: list[float],
    b_values: list[float],
    *,
    rounds: int = 5000,
    seed: int = 20260614,
) -> list[float | None]:
    if not a_values or not b_values:
        return [None, None]
    rng = random.Random(seed)
    diffs: list[float] = []
    for _ in range(rounds):
        a = [rng.choice(a_values) for _ in range(len(a_values))]
        b = [rng.choice(b_values) for _ in range(len(b_values))]
        diffs.append(mean(a) - mean(b))
    diffs.sort()
    lo = diffs[int(0.025 * rounds)]
    hi = diffs[min(rounds - 1, int(0.975 * rounds))]
    return [lo, hi]


def stable_seed(text: str) -> int:
    total = 0
    for idx, char in enumerate(text):
        total += (idx + 1) * ord(char)
    return total


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    successes = sum(1 for row in rows if is_success(row))
    rewards = [as_float(row.get("reward")) for row in rows]
    recovery_attempted = sum(1 for row in rows if row.get("recovery_attempted") is True)
    recovery_success = sum(1 for row in rows if row.get("recovery_success") is True)
    hidden = sum(1 for row in rows if row.get("hidden_business_rule_violation") is True)
    visible = sum(1 for row in rows if visible_signal(row))
    return {
        "n": n,
        "success": successes,
        "success_rate": successes / n if n else None,
        "success_wilson_ci": wilson_ci(successes, n),
        "mean_reward": mean(rewards) if rewards else None,
        "hidden_violation_rate": hidden / n if n else None,
        "visible_signal_rate": visible / n if n else None,
        "recovery_attempted": recovery_attempted,
        "recovery_attempted_rate": recovery_attempted / n if n else None,
        "recovery_success": recovery_success,
        "recovery_success_rate": recovery_success / n if n else None,
    }


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def fmt_ci(ci: list[float | None]) -> str:
    if not ci or ci[0] is None or ci[1] is None:
        return "NA"
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def fmt_rate_count(count: int, n: int) -> str:
    return f"{count} ({count / n:.3f})" if n else "0 (NA)"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        out.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(out)


def file_info(path: Path) -> dict[str, Any]:
    exists = path.exists()
    info: dict[str, Any] = {
        "path": str(path.relative_to(ROOT)),
        "exists": exists,
        "non_empty": False,
        "size_bytes": 0,
        "modified_time": None,
    }
    if exists:
        stat = path.stat()
        info.update(
            {
                "non_empty": stat.st_size > 0,
                "size_bytes": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            }
        )
    return info


def main() -> None:
    status_files = sorted(STATUS_DIR.glob("observability_from_baseline_*_status.jsonl"))
    raw_rows: list[dict[str, Any]] = []
    for path in status_files:
        if "smoke" in path.name:
            continue
        rows = load_jsonl(path)
        for row in rows:
            row["_status_file"] = path.name
        raw_rows.extend(rows)

    formal_rows = [row for row in raw_rows if is_formal_candidate(row)]
    smoke_rows_included = any("smoke" in str(row.get("_status_file", "")) for row in formal_rows)

    status_counts = Counter(str(row.get("status")) for row in formal_rows)
    level_counts = Counter(str(row.get("observability_level")) for row in formal_rows)
    provider_counts = Counter(str(row.get("provider")) for row in formal_rows)
    model_counts = Counter((row.get("env"), row.get("model"), row.get("provider")) for row in formal_rows)

    missing_by_field: dict[str, int] = {}
    for field in CRITICAL_FIELDS:
        missing_by_field[field] = sum(1 for row in formal_rows if field not in row)

    integrity = {
        "expected_total": 525,
        "raw_formal_status_rows_before_filters": len(raw_rows),
        "actual_formal_rows": len(formal_rows),
        "ok": status_counts.get("ok", 0),
        "failed": status_counts.get("failed", 0),
        "timeout": sum(1 for row in formal_rows if row.get("timeout") is True or row.get("status") == "timeout"),
        "provider_error": status_counts.get("provider_error", 0),
        "level_counts": {level: level_counts.get(level, 0) for level in LEVELS},
        "fake_run_count": sum(1 for row in formal_rows if row.get("fake_run") is True),
        "baseline_success_false_count": sum(1 for row in formal_rows if row.get("baseline_success") is not True),
        "wyzlab_count": sum(
            1
            for row in formal_rows
            if row.get("provider") == "wyzlab" or "wyzlab" in str(row.get("model", "")) or "gpt-5.5" in str(row.get("model", ""))
        ),
        "mutation_candidate_count": sum(1 for row in formal_rows if is_mutation_candidate(row)),
        "smoke_rows_included": smoke_rows_included,
        "missing_critical_fields_by_field": missing_by_field,
        "missing_critical_fields_total": sum(missing_by_field.values()),
    }

    overall_by_level = {}
    for level in LEVELS:
        rows = [row for row in formal_rows if row.get("observability_level") == level]
        overall_by_level[level] = summarize_group(rows)

    per_model: list[dict[str, Any]] = []
    grouped: dict[tuple[Any, Any, Any, Any], list[dict[str, Any]]] = defaultdict(list)
    for row in formal_rows:
        grouped[(row.get("env"), row.get("model"), row.get("provider"), row.get("observability_level"))].append(row)
    for (env, model, provider, level) in sorted(grouped.keys(), key=lambda x: (str(x[0]), str(x[1]), str(x[2]), LEVELS.index(x[3]) if x[3] in LEVELS else 999)):
        summary = summarize_group(grouped[(env, model, provider, level)])
        per_model.append(
            {
                "env": env,
                "model": model,
                "provider": provider,
                "observability_level": level,
                **summary,
            }
        )

    def rewards_for(rows: list[dict[str, Any]]) -> list[float]:
        return [as_float(row.get("reward")) for row in rows]

    uplift_overall: dict[str, Any] = {}
    o0_rows = [row for row in formal_rows if row.get("observability_level") == "O0_silent"]
    o0_mean = mean(rewards_for(o0_rows))
    for level in LEVELS[1:]:
        level_rows = [row for row in formal_rows if row.get("observability_level") == level]
        diff = mean(rewards_for(level_rows)) - o0_mean
        uplift_overall[f"{level}-O0_silent"] = {
            "point_estimate": diff,
            "bootstrap_95_ci": bootstrap_diff_ci(rewards_for(level_rows), rewards_for(o0_rows), seed=20260614 + LEVELS.index(level)),
        }

    uplift_by_model: list[dict[str, Any]] = []
    grouped_model: dict[tuple[Any, Any, Any], dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in formal_rows:
        grouped_model[(row.get("env"), row.get("model"), row.get("provider"))][str(row.get("observability_level"))].append(row)
    for (env, model, provider), by_level in sorted(grouped_model.items(), key=lambda x: (str(x[0][0]), str(x[0][1]), str(x[0][2]))):
        base = rewards_for(by_level["O0_silent"])
        base_mean = mean(base) if base else None
        item: dict[str, Any] = {"env": env, "model": model, "provider": provider}
        for level in LEVELS[1:]:
            vals = rewards_for(by_level[level])
            if base_mean is None or not vals:
                item[f"{level}-O0_silent"] = {"point_estimate": None, "bootstrap_95_ci": [None, None]}
            else:
                item[f"{level}-O0_silent"] = {
                    "point_estimate": mean(vals) - base_mean,
                    "bootstrap_95_ci": bootstrap_diff_ci(vals, base, seed=20260614 + stable_seed(f"{model}|{level}")),
                }
        uplift_by_model.append(item)

    monotonicity: list[dict[str, Any]] = []
    for (env, model, provider), by_level in sorted(grouped_model.items(), key=lambda x: (str(x[0][0]), str(x[0][1]), str(x[0][2]))):
        rates = []
        for level in LEVELS:
            rows = by_level[level]
            rates.append(summarize_group(rows)["success_rate"] if rows else None)
        violations = []
        for idx in range(len(LEVELS) - 1):
            left = rates[idx]
            right = rates[idx + 1]
            if left is not None and right is not None and right < left:
                violations.append(
                    {
                        "position": f"{LEVELS[idx + 1]} < {LEVELS[idx]}",
                        "left_rate": left,
                        "right_rate": right,
                    }
                )
        monotonicity.append(
            {
                "env": env,
                "model": model,
                "provider": provider,
                "rates": {level: rates[i] for i, level in enumerate(LEVELS)},
                "is_non_decreasing": not violations,
                "violations": violations,
            }
        )

    semantic_flags: dict[str, Any] = {}
    for level in LEVELS:
        rows = [row for row in formal_rows if row.get("observability_level") == level]
        n = len(rows)
        semantic_flags[level] = {
            "n": n,
            "visible_policy_error_rate": sum(1 for row in rows if row.get("visible_policy_error") is True) / n if n else None,
            "generic_error_visible_rate": sum(1 for row in rows if row.get("generic_error_visible") is True) / n if n else None,
            "structured_policy_error_visible_rate": sum(1 for row in rows if row.get("structured_policy_error_visible") is True) / n if n else None,
            "migration_note_visible_rate": sum(1 for row in rows if row.get("migration_note_visible") is True) / n if n else None,
            "hidden_business_rule_violation_rate": sum(1 for row in rows if row.get("hidden_business_rule_violation") is True) / n if n else None,
            "visible_signal_rate": sum(1 for row in rows if visible_signal(row)) / n if n else None,
        }

    overall_o0 = overall_by_level["O0_silent"]["success_rate"]
    overall_o1 = overall_by_level["O1_generic_error"]["success_rate"]
    overall_o2 = overall_by_level["O2_policy_error"]["success_rate"]
    overall_o3 = overall_by_level["O3_structured_policy_error"]["success_rate"]
    overall_o4 = overall_by_level["O4_migration_note"]["success_rate"]
    clear_gradient = (
        overall_o0 is not None
        and overall_o3 is not None
        and overall_o4 is not None
        and overall_o0 + 0.2 <= overall_o3
        and overall_o0 + 0.2 <= overall_o4
        and all(item["is_non_decreasing"] for item in monotonicity)
    )
    partial_gradient = (
        overall_o0 is not None
        and overall_o3 is not None
        and overall_o4 is not None
        and overall_o3 > overall_o0
        and overall_o4 > overall_o0
    )
    if clear_gradient:
        interpretation_case = "A"
        interpretation = (
            "The formal Phase 5B retail gradient supports the mechanism claim: "
            "agent success increases as the evolved semantic rule becomes more observable."
        )
    elif partial_gradient:
        interpretation_case = "B"
        interpretation = (
            "The results support a weaker but still useful claim: structured diagnostics "
            "and migration notes improve recoverability over silent drift, while generic "
            "or coarse errors are less reliable."
        )
    else:
        interpretation_case = "C"
        interpretation = (
            "The current data does not support a monotonic observability claim; the paper "
            "should retain C4a/C4b as a contrast and treat gradient results as mixed evidence."
        )

    artifact_paths = [
        ROOT / "IEEE_Conference_Template" / "tables" / "observability_gradient_auto.tex",
        ROOT / "IEEE_Conference_Template" / "figures" / "observability_gradient_curve.pdf",
        ROOT / "IEEE_Conference_Template" / "figures" / "observability_uplift_forest.pdf",
    ]
    artifact_status = [file_info(path) for path in artifact_paths]

    summary_info: dict[str, Any] = {}
    if SUMMARY_JSON.exists():
        summary_info = json.loads(SUMMARY_JSON.read_text(encoding="utf-8-sig"))

    packet = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "inputs": {
            "summary_json": str(SUMMARY_JSON.relative_to(ROOT)),
            "summary_md": str(SUMMARY_MD.relative_to(ROOT)),
            "status_files": [str(path.relative_to(ROOT)) for path in status_files],
        },
        "filters": {
            "excluded_smoke_status": True,
            "excluded_fake_run": True,
            "excluded_baseline_success_false": True,
            "excluded_wyzlab": True,
            "excluded_mutation_candidate": True,
        },
        "integrity": integrity,
        "overall_by_level": overall_by_level,
        "per_model_by_level": per_model,
        "uplift_overall": uplift_overall,
        "uplift_by_model": uplift_by_model,
        "monotonicity": monotonicity,
        "semantic_flags": semantic_flags,
        "interpretation": {
            "case": interpretation_case,
            "draft": interpretation,
        },
        "artifact_status": artifact_status,
        "summary_smoke_exclusion": {
            "raw_rows": summary_info.get("raw_rows"),
            "latest_rows": summary_info.get("latest_rows"),
            "fake_rows_excluded": summary_info.get("fake_rows_excluded"),
            "smoke_rows_excluded": summary_info.get("smoke_rows_excluded"),
            "warnings": summary_info.get("warnings", []),
            "observability_gradient_rows": len(summary_info.get("observability_gradient", [])),
            "observability_gradient_paired_total": sum(
                item.get("paired_baseline_successful_count", 0)
                for item in summary_info.get("observability_gradient", [])
            ),
        },
    }

    OUT_JSON.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines.append("# Phase 5C Observability Gradient Review Packet")
    lines.append("")
    lines.append(f"- generated_at: {packet['generated_at']}")
    lines.append("- data source: formal `observability_from_baseline_*_status.jsonl` rows only")
    lines.append("- success definition: `reward >= 0.5`")
    lines.append("- uplift CI: deterministic nonparametric bootstrap over observed rewards, 5,000 rounds")
    lines.append("")

    lines.append("## 1. Integrity Checks")
    lines.append("")
    integrity_rows = [
        ["expected total", integrity["expected_total"]],
        ["actual formal rows", integrity["actual_formal_rows"]],
        ["ok", integrity["ok"]],
        ["failed", integrity["failed"]],
        ["timeout", integrity["timeout"]],
        ["provider_error", integrity["provider_error"]],
        ["fake_run count", integrity["fake_run_count"]],
        ["baseline_success=false count", integrity["baseline_success_false_count"]],
        ["wyzlab count", integrity["wyzlab_count"]],
        ["mutation_candidate count", integrity["mutation_candidate_count"]],
        ["smoke rows included?", "yes" if integrity["smoke_rows_included"] else "no"],
        ["missing critical fields count", integrity["missing_critical_fields_total"]],
    ]
    for level in LEVELS:
        integrity_rows.append([f"{level} count", integrity["level_counts"][level]])
    lines.append(markdown_table(["Check", "Value"], integrity_rows))
    lines.append("")
    lines.append("Critical field missing counts:")
    lines.append(markdown_table(["Field", "Missing"], [[field, count] for field, count in missing_by_field.items()]))
    lines.append("")

    lines.append("## 2. Overall O-Level Success Table")
    lines.append("")
    overall_rows = []
    for level in LEVELS:
        item = overall_by_level[level]
        n = item["n"]
        overall_rows.append(
            [
                level,
                n,
                item["success"],
                fmt(item["success_rate"]),
                fmt_ci(item["success_wilson_ci"]),
                fmt(item["mean_reward"]),
                fmt(item["hidden_violation_rate"]),
                fmt(item["visible_signal_rate"]),
                fmt_rate_count(item["recovery_attempted"], n),
                fmt_rate_count(item["recovery_success"], n),
            ]
        )
    lines.append(
        markdown_table(
            [
                "Level",
                "N",
                "Success",
                "Success rate",
                "Wilson CI",
                "Mean reward",
                "Hidden violation rate",
                "Visible signal rate",
                "Recovery attempted",
                "Recovery success",
            ],
            overall_rows,
        )
    )
    lines.append("")

    lines.append("## 3. Per Model O-Level Table")
    lines.append("")
    per_model_rows = []
    for item in per_model:
        n = item["n"]
        per_model_rows.append(
            [
                item["env"],
                item["model"],
                item["provider"],
                item["observability_level"],
                n,
                item["success"],
                fmt(item["success_rate"]),
                fmt(item["mean_reward"]),
                fmt(item["hidden_violation_rate"]),
                fmt(item["visible_signal_rate"]),
                fmt(item["recovery_success_rate"]),
            ]
        )
    lines.append(
        markdown_table(
            [
                "Env",
                "Model",
                "Provider",
                "Level",
                "N",
                "Success",
                "Rate",
                "Mean reward",
                "Hidden viol.",
                "Visible signal",
                "Recovery success",
            ],
            per_model_rows,
        )
    )
    lines.append("")

    lines.append("## 4. Uplift Table")
    lines.append("")
    overall_uplift_rows = []
    for level in LEVELS[1:]:
        key = f"{level}-O0_silent"
        item = uplift_overall[key]
        overall_uplift_rows.append([key.replace("_silent", ""), fmt(item["point_estimate"]), fmt_ci(item["bootstrap_95_ci"])])
    lines.append("Overall uplift relative to O0:")
    lines.append(markdown_table(["Contrast", "Point estimate", "Bootstrap 95% CI"], overall_uplift_rows))
    lines.append("")
    uplift_rows = []
    for item in uplift_by_model:
        row = [item["env"], item["model"]]
        for level in LEVELS[1:]:
            contrast = item[f"{level}-O0_silent"]
            row.append(f"{fmt(contrast['point_estimate'])} {fmt_ci(contrast['bootstrap_95_ci'])}")
        uplift_rows.append(row)
    lines.append(markdown_table(["Env", "Model", "O1-O0", "O2-O0", "O3-O0", "O4-O0"], uplift_rows))
    lines.append("")

    lines.append("## 5. Monotonicity / Mechanism Check")
    lines.append("")
    mono_rows = []
    for item in monotonicity:
        violations = "; ".join(v["position"] for v in item["violations"]) if item["violations"] else "none"
        rate_text = ", ".join(f"{level}={fmt(item['rates'][level])}" for level in LEVELS)
        mono_rows.append([item["env"], item["model"], item["provider"], "yes" if item["is_non_decreasing"] else "no", violations, rate_text])
    lines.append(markdown_table(["Env", "Model", "Provider", "Non-decreasing?", "Violations", "Rates"], mono_rows))
    lines.append("")

    lines.append("## 6. Expected Semantic Flags")
    lines.append("")
    flag_rows = []
    for level in LEVELS:
        item = semantic_flags[level]
        flag_rows.append(
            [
                level,
                item["n"],
                fmt(item["visible_policy_error_rate"]),
                fmt(item["generic_error_visible_rate"]),
                fmt(item["structured_policy_error_visible_rate"]),
                fmt(item["migration_note_visible_rate"]),
                fmt(item["hidden_business_rule_violation_rate"]),
                fmt(item["visible_signal_rate"]),
            ]
        )
    lines.append(
        markdown_table(
            [
                "Level",
                "N",
                "visible_policy_error",
                "generic_error_visible",
                "structured_policy_error_visible",
                "migration_note_visible",
                "hidden_business_rule_violation",
                "visible_signal",
            ],
            flag_rows,
        )
    )
    lines.append("")

    lines.append("## 7. Recommended Paper Interpretation")
    lines.append("")
    lines.append(f"- case: {interpretation_case}")
    lines.append(f"- draft: {interpretation}")
    lines.append("")

    lines.append("## 8. LaTeX Table And Figure Checks")
    lines.append("")
    artifact_rows = [
        [
            item["path"],
            "yes" if item["exists"] else "no",
            "yes" if item["non_empty"] else "no",
            item["size_bytes"],
            item["modified_time"] or "NA",
        ]
        for item in artifact_status
    ]
    lines.append(markdown_table(["Path", "Exists", "Non-empty", "Size bytes", "Modified time"], artifact_rows))
    lines.append("")

    lines.append("## 9. Smoke Contamination Check")
    lines.append("")
    smoke = packet["summary_smoke_exclusion"]
    smoke_rows = [
        ["summary raw rows", smoke["raw_rows"]],
        ["summary latest rows", smoke["latest_rows"]],
        ["fake rows excluded", smoke["fake_rows_excluded"]],
        ["smoke rows excluded", smoke["smoke_rows_excluded"]],
        ["summary warnings", "; ".join(smoke["warnings"])],
        ["observability gradient rows", smoke["observability_gradient_rows"]],
        ["observability gradient paired total", smoke["observability_gradient_paired_total"]],
    ]
    lines.append(markdown_table(["Check", "Value"], smoke_rows))
    lines.append("")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"review_packet_md={OUT_MD}")
    print(f"review_packet_json={OUT_JSON}")
    print(f"formal_rows={len(formal_rows)}")
    print(f"ok={integrity['ok']} failed={integrity['failed']} timeout={integrity['timeout']} provider_error={integrity['provider_error']}")
    print(f"interpretation_case={interpretation_case}")


if __name__ == "__main__":
    main()
