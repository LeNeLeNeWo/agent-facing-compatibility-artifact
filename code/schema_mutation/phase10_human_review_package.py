"""Build Phase 10B human-review packages from Phase 10A artifacts.

This script is offline-only: it reads existing Phase 10A JSON/JSONL artifacts
and writes annotation sheets plus reviewer guidelines. It does not run models or
modify raw artifacts.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent.parent
PHASE10 = ROOT / "runs" / "schema_mutation" / "phase10"
OUT = PHASE10 / "phase10b"
HUMAN_REVIEW = OUT / "human_review"
ORACLE_REVIEW = OUT / "oracle_review"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def bool_text(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return ""
    return str(value)


def clipped(value: Any, limit: int = 280) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "..."


def markdown_table(rows: list[dict[str, Any]], fields: list[str], limit: int | None = None) -> str:
    shown = rows if limit is None else rows[:limit]
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in shown:
        values = [clipped(row.get(field, ""), 120).replace("|", "\\|") for field in fields]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_api_annotation_sheet() -> dict[str, Any]:
    corpus_path = PHASE10 / "real_api_grounding" / "api_evolution_corpus.jsonl"
    rows = read_jsonl(corpus_path)
    fields = [
        "entry_id",
        "provider",
        "date",
        "title",
        "url",
        "short_paraphrase",
        "evidence_snippet",
        "auto_taxonomy_class",
        "auto_c_subclass",
        "auto_schema_visible",
        "auto_runtime_visible",
        "auto_agent_task_relevance",
        "auto_label_rationale",
        "human_taxonomy_class",
        "human_c_subclass",
        "human_schema_visible",
        "human_runtime_visible",
        "human_agent_task_relevance",
        "human_confidence",
        "human_notes",
        "accept_for_paper_example",
    ]
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        out_rows.append(
            {
                "entry_id": row.get("entry_id"),
                "provider": row.get("provider"),
                "date": row.get("date"),
                "title": row.get("title"),
                "url": row.get("url"),
                "short_paraphrase": row.get("short_paraphrase"),
                "evidence_snippet": row.get("evidence_snippet"),
                "auto_taxonomy_class": row.get("taxonomy_class"),
                "auto_c_subclass": row.get("c_subclass"),
                "auto_schema_visible": bool_text(row.get("schema_visible")),
                "auto_runtime_visible": row.get("runtime_visible"),
                "auto_agent_task_relevance": row.get("agent_task_relevance"),
                "auto_label_rationale": row.get("label_rationale"),
                "human_taxonomy_class": "",
                "human_c_subclass": "",
                "human_schema_visible": "",
                "human_runtime_visible": "",
                "human_agent_task_relevance": "",
                "human_confidence": "",
                "human_notes": "",
                "accept_for_paper_example": "",
            }
        )
    write_csv(HUMAN_REVIEW / "api_evolution_annotation_sheet.csv", out_rows, fields)
    providers = sorted({str(row.get("provider")) for row in rows})
    counts = Counter(str(row.get("taxonomy_class")) for row in rows)
    c_candidates = sum(1 for row in rows if row.get("taxonomy_class") == "C")
    md = [
        "# API Evolution Annotation Sheet",
        "",
        "This sheet converts the Phase 10A automatically labeled public-changelog corpus into a human-review queue. The automatic labels are candidates only.",
        "",
        f"- Entries: {len(rows)}",
        f"- Providers: {len(providers)} ({', '.join(providers)})",
        f"- C-class candidates: {c_candidates}",
        "- Taxonomy distribution: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        "",
        "## Fields",
        "",
        "- `auto_*` columns are machine-generated labels from Phase 10A.",
        "- `human_*` columns are intentionally blank for reviewer annotation.",
        "- `accept_for_paper_example` should be marked only after source evidence and semantic interpretation are manually checked.",
        "",
        "## Preview",
        "",
        markdown_table(out_rows, ["entry_id", "provider", "date", "auto_taxonomy_class", "auto_c_subclass", "auto_schema_visible", "url"], limit=20),
        "",
    ]
    (HUMAN_REVIEW / "api_evolution_annotation_sheet.md").write_text("\n".join(md), encoding="utf-8")
    return {"entries": len(rows), "providers": len(providers), "c_candidates": c_candidates}


def build_candidate_review_sheet() -> dict[str, Any]:
    path = PHASE10 / "real_api_grounding" / "real_change_case_candidates.json"
    candidates = json.loads(path.read_text(encoding="utf-8"))
    fields = [
        "case_id",
        "provider",
        "real_change_type",
        "source_url",
        "before_semantics",
        "after_semantics",
        "why_schema_invisible_or_semantic",
        "possible_tool_schema",
        "possible_old_api_wrapper_behavior",
        "possible_new_api_wrapper_behavior",
        "possible_oracle",
        "agent_task_template",
        "official_source_evidence_sufficient",
        "before_after_semantics_clear",
        "schema_invisible_or_semantic_contract_clear",
        "can_construct_deterministic_wrapper",
        "can_construct_agent_task",
        "can_construct_oracle",
        "best_candidate_for_phase10c",
        "human_confidence",
        "risks",
        "human_notes",
    ]
    out_rows: list[dict[str, Any]] = []
    for row in candidates:
        out = {field: row.get(field, "") for field in fields}
        out.update(
            {
                "official_source_evidence_sufficient": "",
                "before_after_semantics_clear": "",
                "schema_invisible_or_semantic_contract_clear": "",
                "can_construct_deterministic_wrapper": "",
                "can_construct_agent_task": "",
                "can_construct_oracle": "",
                "best_candidate_for_phase10c": "",
                "human_confidence": "",
                "human_notes": "",
            }
        )
        out_rows.append(out)
    write_csv(HUMAN_REVIEW / "real_case_candidate_review_sheet.csv", out_rows, fields)
    md = [
        "# Real Case Candidate Review Sheet",
        "",
        "These three candidates are not treated as fully validated examples. Reviewers should inspect the official source URL and decide whether each case is suitable for a deterministic Phase 10C replay.",
        "",
        markdown_table(out_rows, ["case_id", "provider", "real_change_type", "source_url", "possible_oracle", "risks"], limit=None),
        "",
        "## Reviewer Decisions Needed",
        "",
        "- Is the official source evidence sufficient?",
        "- Are before/after semantics clear enough for a wrapper?",
        "- Is the schema-invisible or semantic-contract nature clear?",
        "- Can we construct a deterministic wrapper, agent task, and oracle?",
        "- Which candidate is the best Phase 10C real-case replay target?",
        "",
    ]
    (HUMAN_REVIEW / "real_case_candidate_review_sheet.md").write_text("\n".join(md), encoding="utf-8")
    return {"case_candidates": len(out_rows)}


def write_annotation_guidelines() -> None:
    text = """# Phase 10B API Evolution Annotation Guidelines

## Scope

Review only public official source URLs and the short evidence snippets in the sheet. The automatic labels are candidates, not validated labels.

## A/B/C/D Taxonomy

- A surface/representation change: names, formats, descriptions, examples, or representation details change without a clear schema-contract or semantic-contract change.
- B schema-contract change: request/response types, requiredness, enum values, field presence, or typed client compatibility changes.
- C semantic-contract change: endpoint, field names, JSON types, and call signature can stay stable while task semantics change.
- D protocol/operational change: authentication, permissions, pagination, rate limits, error envelope, transport, or operational protocol changes dominate the compatibility risk.
- mixed: use when the entry clearly combines multiple classes and one class is not dominant.
- unclear: use when the official evidence is insufficient.

## C Subclasses

- C1 unit/scale drift: numeric interpretation, units, precision, scale, thresholds, or validation ranges change while schema shape remains stable.
- C2 currency/locale drift: currency, locale, timezone, language, regional behavior, or formatting semantics change.
- C3 default behavior drift: omitted or optional inputs keep the same schema but produce a changed default outcome.
- C4 business-rule drift: eligibility, payment, refund, policy, workflow, approval, restriction, or domain rule changes while the call surface can remain stable.
- none/unclear: use when the entry is C-like but the subclass is not supported by the evidence.

## Visibility Labels

- schema-invisible means the official change could plausibly preserve endpoint, field names, JSON types, and typed call signature while changing behavior.
- schema-visible means a conventional schema or typed-client check should plausibly detect the change.
- runtime-visible means the evolved API exposes an error, diagnostic, migration note, or other visible signal during the task.
- runtime-invisible means the task can appear locally successful and the changed rule is only detected by final-state/oracle validation.
- unknown is preferred when the changelog does not clearly state runtime behavior.

## Confidence

- high-confidence C-class requires official evidence for a semantic behavior change and a plausible unchanged call surface.
- medium-confidence means the semantic interpretation is plausible but a reviewer must inspect more context.
- low-confidence means the automatic label is weak and should not be used as a paper example without stronger evidence.

## Conservative Review Rules

- If uncertain, mark `unclear`; do not force a taxonomy label.
- Use only official source URLs and short evidence snippets.
- Do not infer production frequency, incident rate, or user impact from this corpus.
- The corpus supports a claim about public changelog grounding, not production base rates.
"""
    (HUMAN_REVIEW / "annotation_guidelines.md").write_text(text, encoding="utf-8")


def build_oracle_review() -> dict[str, Any]:
    rows = read_jsonl(PHASE10 / "oracle_validation" / "oracle_validation_packet.jsonl")
    fields = [
        "sample_id",
        "domain",
        "model",
        "condition",
        "c_class",
        "task_id",
        "mutation_rule",
        "tool_call_summary",
        "final_state_summary",
        "oracle_flag",
        "reward",
        "auto_explanation",
        "trace_pointer",
        "human_oracle_correct",
        "human_failure_type",
        "human_confidence",
        "human_notes",
    ]
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        out_rows.append(
            {
                "sample_id": row.get("sample_id"),
                "domain": row.get("env"),
                "model": row.get("model"),
                "condition": row.get("condition"),
                "c_class": row.get("semantic_class"),
                "task_id": row.get("task_id"),
                "mutation_rule": row.get("mutation_rule"),
                "tool_call_summary": row.get("tool_call_summary"),
                "final_state_summary": row.get("relevant_final_state"),
                "oracle_flag": bool_text(row.get("oracle_rule_violation")),
                "reward": row.get("reward"),
                "auto_explanation": row.get("oracle_explanation"),
                "trace_pointer": row.get("raw_trace_pointer") or row.get("source_artifact"),
                "human_oracle_correct": "",
                "human_failure_type": "",
                "human_confidence": "",
                "human_notes": "",
            }
        )
    write_csv(ORACLE_REVIEW / "oracle_review_sheet.csv", out_rows, fields)
    categories = Counter(str(row.get("sample_category")) for row in rows)
    baseline = [row for row in rows if row.get("sample_category") == "baseline_success_unmutated"]
    baseline_rate = (
        sum(1 for row in baseline if row.get("oracle_rule_violation")) / len(baseline)
        if baseline
        else 0.0
    )
    guideline = """# Phase 10B Oracle Review Guidelines

Reviewers should inspect the trace pointer, tool-call summary, final-state summary, and evolved rule. The goal is to validate whether the deterministic oracle label matches the intended semantic rule.

## Review Questions

- Does `oracle_flag` agree with the evolved rule?
- Is a positive O0 case truly a compliant semantic failure: syntactically valid call, unchanged schema/call surface, no visible policy signal, but final state violates the evolved rule?
- Should the baseline unmutated case avoid triggering the oracle?
- Is an O0 negative truly a non-violation?
- Is a recovered case truly a recovery rather than an unrelated success?
- If the task, wrapper behavior, or final state is ambiguous, mark the sample `suspicious`.

## Labels

- `human_oracle_correct`: yes / no / unclear / suspicious.
- `human_failure_type`: compliant_semantic_failure / visible_recovery / non_violation / infrastructure / ambiguous / other.
- `human_confidence`: high / medium / low.

Do not calculate inter-annotator agreement until two independent human label sets exist.
"""
    (ORACLE_REVIEW / "oracle_review_guidelines.md").write_text(guideline, encoding="utf-8")
    summary = [
        "# Oracle Review Summary",
        "",
        f"- Samples: {len(rows)}",
        "- Categories: " + ", ".join(f"{k}={v}" for k, v in sorted(categories.items())),
        f"- Baseline oracle violation rate from Phase 10A packet: {baseline_rate:.1%}",
        "- Human labels needed: `human_oracle_correct`, `human_failure_type`, `human_confidence`, `human_notes`.",
        "",
        "No human-validated precision claim should be made until this sheet is manually reviewed.",
        "",
    ]
    (ORACLE_REVIEW / "oracle_review_summary.md").write_text("\n".join(summary), encoding="utf-8")
    return {"oracle_samples": len(rows), "baseline_violation_rate": baseline_rate, "categories": dict(categories)}


def main() -> int:
    HUMAN_REVIEW.mkdir(parents=True, exist_ok=True)
    ORACLE_REVIEW.mkdir(parents=True, exist_ok=True)
    api = build_api_annotation_sheet()
    cases = build_candidate_review_sheet()
    write_annotation_guidelines()
    oracle = build_oracle_review()
    manifest = {"api": api, "cases": cases, "oracle": oracle}
    (OUT / "human_review_package_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
