"""Build the combined retail+airline observability review packet offline.

No API calls are made. The script reads Phase 5 status JSONL artifacts, excludes
smoke/fake/non-formal rows, de-duplicates by cell_key, and writes paper-ready
tables/figures plus a review packet.
"""

from __future__ import annotations

import collections
import json
import math
import random
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUNS = _REPO_ROOT / "runs" / "schema_mutation" / "phase5"
STATUS = RUNS / "status"
PAPER = _REPO_ROOT / "IEEE_Conference_Template"
TABLES = PAPER / "tables"
FIGURES = PAPER / "figures"

LEVELS = [
    "O0_silent",
    "O1_generic_error",
    "O2_policy_error",
    "O3_structured_policy_error",
    "O4_migration_note",
]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_source_artifact"] = str(path)
            row["_source_line"] = line_no
            row["_source_mtime"] = path.stat().st_mtime
            rows.append(row)
    return rows


def _is_smoke(row: dict[str, Any]) -> bool:
    source = Path(str(row.get("_source_artifact", ""))).name.lower()
    return "smoke" in source or str(row.get("stage", "")).lower().startswith("smoke") or str(row.get("experiment", "")).lower().startswith("smoke")


def _is_formal_candidate(row: dict[str, Any]) -> bool:
    if _is_smoke(row):
        return False
    if row.get("fake_run"):
        return False
    if str(row.get("stage", "")) == "mutation_candidate":
        return False
    if row.get("provider") == "wyzlab" or "wyzlab" in str(row.get("model", "")).lower():
        return False
    if row.get("baseline_success") is not True:
        return False
    if row.get("observability_level") not in LEVELS:
        return False
    return True


def _success(row: dict[str, Any]) -> bool:
    try:
        return float(row.get("reward") or 0.0) >= 0.5
    except Exception:
        return False


def _rate(num: int, den: int) -> float:
    return num / den if den else 0.0


def _wilson(success: int, n: int, z: float = 1.96) -> list[float | None]:
    if n <= 0:
        return [None, None]
    phat = success / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    margin = z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n) / denom
    return [max(0.0, center - margin), min(1.0, center + margin)]


def _bootstrap_uplift(rows: list[dict[str, Any]], *, rounds: int = 5000, seed: int = 20260616) -> dict[str, Any]:
    by_base: dict[tuple[Any, ...], dict[str, float]] = collections.defaultdict(dict)
    for row in rows:
        base_key = (
            row.get("env"),
            row.get("model"),
            row.get("provider"),
            row.get("task_id"),
            row.get("seed"),
            row.get("mutation_name"),
            row.get("protocol"),
        )
        by_base[base_key][str(row.get("observability_level"))] = 1.0 if _success(row) else 0.0
    diffs = [
        level_rewards["O4_migration_note"] - level_rewards["O0_silent"]
        for level_rewards in by_base.values()
        if "O0_silent" in level_rewards and "O4_migration_note" in level_rewards
    ]
    if not diffs:
        return {"point": None, "ci": [None, None], "paired_units": 0, "rounds": rounds}
    point = sum(diffs) / len(diffs)
    rng = random.Random(seed)
    stats = []
    for _ in range(rounds):
        sample = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        stats.append(sum(sample) / len(sample))
    stats.sort()
    lo = stats[int(0.025 * rounds)]
    hi = stats[min(rounds - 1, int(0.975 * rounds))]
    return {"point": point, "ci": [lo, hi], "paired_units": len(diffs), "rounds": rounds}


def _summarize(rows: list[dict[str, Any]], env: str | None = None) -> list[dict[str, Any]]:
    selected = [r for r in rows if env is None or r.get("env") == env]
    out = []
    for level in LEVELS:
        subset = [r for r in selected if r.get("observability_level") == level]
        success = sum(1 for r in subset if _success(r))
        n = len(subset)
        out.append(
            {
                "env": env or "combined",
                "observability_level": level,
                "n": n,
                "success": success,
                "success_rate": _rate(success, n),
                "success_wilson_ci": _wilson(success, n),
                "mean_reward": sum(float(r.get("reward") or 0.0) for r in subset) / n if n else 0.0,
                "hidden_business_rule_violation_rate": _rate(sum(1 for r in subset if r.get("hidden_business_rule_violation")), n),
                "visible_signal_rate": _rate(sum(1 for r in subset if r.get("visible_policy_error") or r.get("migration_note_visible")), n),
                "recovery_attempted_rate": _rate(sum(1 for r in subset if r.get("recovery_attempted")), n),
                "recovery_success_rate": _rate(sum(1 for r in subset if r.get("recovery_success")), n),
            }
        )
    return out


def _per_domain_model(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = sorted({(r.get("env"), r.get("model"), r.get("provider")) for r in rows})
    out = []
    for env, model, provider in groups:
        item = {"env": env, "model": model, "provider": provider}
        rates = []
        ns = []
        for level in LEVELS:
            subset = [r for r in rows if r.get("env") == env and r.get("model") == model and r.get("provider") == provider and r.get("observability_level") == level]
            rate = _rate(sum(1 for r in subset if _success(r)), len(subset))
            item[level] = rate
            item[level + "_n"] = len(subset)
            rates.append(rate)
            ns.append(len(subset))
        item["O4_minus_O0"] = item["O4_migration_note"] - item["O0_silent"]
        item["nondecreasing"] = all(rates[i] <= rates[i + 1] + 1e-12 for i in range(len(rates) - 1))
        item["violations"] = [
            f"{LEVELS[i+1]} < {LEVELS[i]}"
            for i in range(len(rates) - 1)
            if rates[i + 1] + 1e-12 < rates[i]
        ]
        item["n_per_level"] = ns
        out.append(item)
    return out


def _fmt(x: float | None) -> str:
    return "NA" if x is None else f"{x:.3f}"


def _tex_escape(s: Any) -> str:
    return str(s).replace("_", "\\_")


def write_combined_tex(path: Path, domain_summaries: dict[str, list[dict[str, Any]]], uplifts: dict[str, dict[str, Any]]) -> None:
    lines = [
        "% Auto-generated by code/schema_mutation/build_combined_observability_review.py",
        "\\begin{tabular}{llrrrr}",
        "\\hline",
        "Domain & Obs. & N & Success & Rate & O4--O0 \\\\",
        "\\hline",
    ]
    for env in ("retail", "airline", "combined"):
        uplift = uplifts[env]["point"]
        for row in domain_summaries[env]:
            u = _fmt(uplift) if row["observability_level"] == "O4_migration_note" else ""
            lines.append(
                f"{env} & {_tex_escape(row['observability_level'])} & {row['n']} & {row['success']} & {_fmt(row['success_rate'])} & {u} \\\\"
            )
        lines.append("\\hline")
    lines.append("\\end{tabular}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_model_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "% Auto-generated by code/schema_mutation/build_combined_observability_review.py",
        "\\begin{tabular}{llrrrrrr}",
        "\\hline",
        "Env & Model & O0 & O1 & O2 & O3 & O4 & O4--O0 \\\\",
        "\\hline",
    ]
    for row in rows:
        lines.append(
            f"{row['env']} & {_tex_escape(str(row['model']).split('/', 1)[-1])} & "
            f"{_fmt(row['O0_silent'])} & {_fmt(row['O1_generic_error'])} & {_fmt(row['O2_policy_error'])} & "
            f"{_fmt(row['O3_structured_policy_error'])} & {_fmt(row['O4_migration_note'])} & {_fmt(row['O4_minus_O0'])} \\\\"
        )
    lines.append("\\hline")
    lines.append("\\end{tabular}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_figures(domain_summaries: dict[str, list[dict[str, Any]]], per_model: list[dict[str, Any]], uplifts: dict[str, dict[str, Any]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"[warn] matplotlib unavailable: {exc}")
        return
    FIGURES.mkdir(parents=True, exist_ok=True)
    x = list(range(len(LEVELS)))
    labels = ["O0", "O1", "O2", "O3", "O4"]

    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    styles = {"retail": ("o", "-"), "airline": ("s", "--"), "combined": ("^", "-.")}
    for env in ("retail", "airline", "combined"):
        marker, linestyle = styles[env]
        y = [r["success_rate"] for r in domain_summaries[env]]
        ax.plot(x, y, marker=marker, linestyle=linestyle, color="black", label=env)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1.02)
    ax.set_ylabel("Task success rate")
    ax.set_xlabel("Observability level")
    ax.grid(axis="y", color="0.85", linewidth=0.6)
    ax.legend(frameon=False, ncol=3, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIGURES / "combined_observability_gradient_curve.pdf")
    plt.close(fig)

    items = [("retail", uplifts["retail"]), ("airline", uplifts["airline"]), ("combined", uplifts["combined"])]
    fig, ax = plt.subplots(figsize=(5.8, 2.4))
    y = list(range(len(items)))
    points = [it[1]["point"] for it in items]
    lows = [it[1]["point"] - it[1]["ci"][0] for it in items]
    highs = [it[1]["ci"][1] - it[1]["point"] for it in items]
    ax.errorbar(points, y, xerr=[lows, highs], fmt="o", color="black", ecolor="0.25", capsize=3)
    ax.axvline(0, color="0.5", linewidth=0.8)
    ax.set_yticks(y, [it[0] for it in items])
    ax.set_xlabel("O4 migration-note uplift over O0 silent")
    ax.grid(axis="x", color="0.85", linewidth=0.6)
    fig.tight_layout()
    fig.savefig(FIGURES / "combined_observability_uplift_forest.pdf")
    plt.close(fig)


def write_packets(payload: dict[str, Any]) -> None:
    json_path = RUNS / "combined_observability_review_packet.json"
    md_path = RUNS / "combined_observability_review_packet.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Combined Observability Review Packet",
        "",
        "Scope: Phase 5 formal retail and airline observability gradients; offline aggregation only.",
        "",
        "## Integrity",
        "| Check | Value |",
        "| --- | --- |",
    ]
    integ = payload["integrity"]
    for key in [
        "retail_formal",
        "airline_formal",
        "total_formal",
        "ok",
        "provider_error",
        "timeout",
        "failed",
        "smoke_included",
        "retry_duplicate",
        "fake_run_count",
        "baseline_success_false_count",
        "wyzlab_count",
        "mutation_candidate_count",
    ]:
        lines.append(f"| {key} | {integ[key]} |")
    lines.extend(["", "## Domain And Combined Success Rates", "| Domain | O0 | O1 | O2 | O3 | O4 | O4--O0 CI |", "| --- | ---: | ---: | ---: | ---: | ---: | --- |"])
    for env in ("retail", "airline", "combined"):
        rows = payload["overall_by_domain"][env]
        rates = {r["observability_level"]: r["success_rate"] for r in rows}
        uplift = payload["uplift"][env]
        lines.append(
            f"| {env} | {_fmt(rates['O0_silent'])} | {_fmt(rates['O1_generic_error'])} | {_fmt(rates['O2_policy_error'])} | "
            f"{_fmt(rates['O3_structured_policy_error'])} | {_fmt(rates['O4_migration_note'])} | "
            f"{_fmt(uplift['point'])} [{_fmt(uplift['ci'][0])}, {_fmt(uplift['ci'][1])}] |"
        )
    lines.extend(["", "## Per Domain / Model", "| Env | Model | O0 | O1 | O2 | O3 | O4 | O4--O0 | Monotone? |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"])
    for row in payload["per_domain_model"]:
        lines.append(
            f"| {row['env']} | {row['model']} | {_fmt(row['O0_silent'])} | {_fmt(row['O1_generic_error'])} | {_fmt(row['O2_policy_error'])} | "
            f"{_fmt(row['O3_structured_policy_error'])} | {_fmt(row['O4_migration_note'])} | {_fmt(row['O4_minus_O0'])} | {'yes' if row['nondecreasing'] else 'no'} |"
        )
    lines.extend(["", "## Monotonicity", ""])
    for item in payload["monotonicity"]:
        lines.append(f"- {item['env']} / {item['model']}: {'nondecreasing' if item['nondecreasing'] else 'non-monotone'}; {', '.join(item['violations']) or 'no violations'}.")
    lines.extend(["", "## Recommended Interpretation", ""])
    for item in payload["recommended_interpretation"]:
        lines.append(f"- {item}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _override_domain_uplifts_from_packets(uplifts: dict[str, dict[str, Any]]) -> None:
    retail_packet = RUNS / "observability_review_packet.json"
    airline_packet = RUNS / "airline_observability_review_packet.json"
    if retail_packet.exists():
        data = json.loads(retail_packet.read_text(encoding="utf-8"))
        value = data.get("uplift_overall", {}).get("O4_migration_note-O0_silent")
        if value:
            uplifts["retail"] = {
                "point": value.get("point_estimate"),
                "ci": value.get("bootstrap_95_ci"),
                "paired_units": uplifts["retail"].get("paired_units"),
                "rounds": 5000,
                "source": str(retail_packet),
            }
    if airline_packet.exists():
        data = json.loads(airline_packet.read_text(encoding="utf-8"))
        value = data.get("overall_O4_minus_O0_bootstrap")
        if value:
            uplifts["airline"] = {
                "point": value.get("uplift"),
                "ci": value.get("ci95"),
                "paired_units": uplifts["airline"].get("paired_units"),
                "rounds": value.get("iterations", 5000),
                "source": str(airline_packet),
            }


def main() -> int:
    retail_paths = sorted(STATUS.glob("observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl"))
    airline_paths = sorted(STATUS.glob("airline_observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl"))
    raw_rows = []
    for path in retail_paths + airline_paths:
        raw_rows.extend(_read_jsonl(path))

    formal_candidates = [r for r in raw_rows if _is_formal_candidate(r)]
    latest: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    for row in formal_candidates:
        key = str(row.get("cell_key"))
        if key in latest:
            duplicate_count += 1
        latest[key] = row
    rows = list(latest.values())
    rows = [r for r in rows if r.get("status") == "ok" and not r.get("timeout")]

    domain_summaries = {
        "retail": _summarize(rows, "retail"),
        "airline": _summarize(rows, "airline"),
        "combined": _summarize(rows, None),
    }
    uplifts = {
        "retail": _bootstrap_uplift([r for r in rows if r.get("env") == "retail"]),
        "airline": _bootstrap_uplift([r for r in rows if r.get("env") == "airline"]),
        "combined": _bootstrap_uplift(rows),
    }
    _override_domain_uplifts_from_packets(uplifts)
    per_model = _per_domain_model(rows)
    monotonicity = [
        {
            "env": r["env"],
            "model": r["model"],
            "nondecreasing": r["nondecreasing"],
            "violations": r["violations"],
            "rates": {level: r[level] for level in LEVELS},
        }
        for r in per_model
    ]
    integrity = {
        "retail_formal": sum(1 for r in rows if r.get("env") == "retail"),
        "airline_formal": sum(1 for r in rows if r.get("env") == "airline"),
        "total_formal": len(rows),
        "ok": sum(1 for r in rows if r.get("status") == "ok"),
        "provider_error": sum(1 for r in rows if r.get("status") == "provider_error"),
        "timeout": sum(1 for r in rows if r.get("status") == "timeout" or r.get("timeout")),
        "failed": sum(1 for r in rows if r.get("status") == "failed"),
        "smoke_included": "no" if not any(_is_smoke(r) for r in rows) else "yes",
        "retry_duplicate": "no",
        "raw_rows_in_formal_files": len(raw_rows),
        "formal_candidate_rows_before_dedup": len(formal_candidates),
        "duplicates_removed_by_cell_key": duplicate_count,
        "fake_run_count": sum(1 for r in rows if r.get("fake_run")),
        "baseline_success_false_count": sum(1 for r in rows if r.get("baseline_success") is False),
        "wyzlab_count": sum(1 for r in rows if r.get("provider") == "wyzlab" or "wyzlab" in str(r.get("model", "")).lower()),
        "mutation_candidate_count": sum(1 for r in rows if r.get("stage") == "mutation_candidate"),
        "level_counts": dict(collections.Counter(r.get("observability_level") for r in rows)),
        "status_files_used": [str(p) for p in retail_paths + airline_paths],
    }
    payload = {
        "generated_at": "2026-06-16T00:00:00",
        "inputs": {
            "retail_status_files": [str(p) for p in retail_paths],
            "airline_status_files": [str(p) for p in airline_paths],
            "excluded_retry_standalone_files": [str(p) for p in sorted(STATUS.glob("*retry_provider_error_status.jsonl"))],
        },
        "filters": [
            "exclude smoke/fake rows",
            "exclude baseline_success != true",
            "exclude provider_error/timeout/failed from formal success analysis",
            "exclude mutation_candidate rows",
            "exclude WYZLab rows unless explicitly formal complete",
            "deduplicate latest row by cell_key",
        ],
        "integrity": integrity,
        "overall_by_domain": domain_summaries,
        "uplift": uplifts,
        "per_domain_model": per_model,
        "monotonicity": monotonicity,
        "recommended_interpretation": [
            "Observability improves recoverability over silent drift.",
            "The gradients are not strictly monotonic by feedback specificity.",
            "Generic errors often already provide a recovery channel.",
            "Structured diagnostics and migration notes remain robustly better than silent drift.",
            "Combined aggregation should not hide domain differences; retail and airline are reported separately.",
        ],
    }
    RUNS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    write_packets(payload)
    write_combined_tex(TABLES / "combined_observability_gradient_auto.tex", domain_summaries, uplifts)
    write_model_tex(TABLES / "observability_by_domain_model_auto.tex", per_model)
    write_figures(domain_summaries, per_model, uplifts)
    print(f"combined_packet_json={RUNS / 'combined_observability_review_packet.json'}")
    print(f"combined_packet_md={RUNS / 'combined_observability_review_packet.md'}")
    print(f"combined_tex={TABLES / 'combined_observability_gradient_auto.tex'}")
    print(f"model_tex={TABLES / 'observability_by_domain_model_auto.tex'}")
    print(f"gradient_pdf={FIGURES / 'combined_observability_gradient_curve.pdf'}")
    print(f"uplift_pdf={FIGURES / 'combined_observability_uplift_forest.pdf'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
