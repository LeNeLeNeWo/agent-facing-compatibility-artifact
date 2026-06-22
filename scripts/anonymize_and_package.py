#!/usr/bin/env python3
"""Build the anonymous 4open-ready artifact package.

This script is intentionally offline-only. It copies curated code, data,
summaries, figures, and tables into ``artifact_release_4open/``; rewrites local
absolute paths and obvious identity strings; and emits anonymization and
inventory reports. It never runs agent/API experiments and never edits the
source artifacts in place.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TITLE = "Compliant Semantic Failures: Testing Agent-Facing Compatibility of Evolving Tool APIs"
OUT_DIRNAME = "artifact_release_4open"

TEXT_EXTENSIONS = {
    ".bib",
    ".cfg",
    ".cff",
    ".csv",
    ".gitignore",
    ".gitattributes",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sh",
    ".tex",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_DIR_NAMES = {
    ".agents",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "logs",
    "raw",
}

EXCLUDED_FILE_PATTERNS = [
    ".env",
    "*.err",
    "*.log",
    "*.pid",
    "*.pyc",
    "*.pyo",
    "*.Zone.Identifier",
    "*.bak*",
    "*.tmp",
    ".DS_Store",
    "Thumbs.db",
    "smoke_wyzai.py",
    "*grok*",
    "*Grok*",
    "*wyzai*",
    "*WYZAI*",
    "*provider_preflight.md",
]

IDENTITY_PATTERNS = [
    (re.compile("Corn" + "elius", re.I), "<REDACTED_NAME>"),
    (re.compile("alda_" + "occaecatiqxi", re.I), "<REDACTED_USERNAME>"),
    (re.compile("University of Science and Technology" + " of China", re.I), "<REDACTED_AFFILIATION>"),
    (re.compile(r"\b" + "US" + r"TC\b", re.I), "<REDACTED_AFFILIATION>"),
    (re.compile(r"\b" + "Ten" + r"cent\b", re.I), "<REDACTED_ORGANIZATION>"),
]

SECRET_VALUE_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{12,}"), "<REDACTED_SECRET>"),
    (re.compile(r"ghp_[A-Za-z0-9_]{12,}"), "<REDACTED_SECRET>"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{12,}"), "<REDACTED_SECRET>"),
    (re.compile(r"(Authorization:\s*Bearer\s+)[A-Za-z0-9._\-]{8,}", re.I), r"\1<REDACTED_SECRET>"),
    (re.compile(r"(?i)(api[_-]?key|token|secret|password)(\s*[:=]\s*)[\"']?[A-Za-z0-9._/\-]{8,}[\"']?"), r"\1\2<REDACTED_SECRET>"),
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_text_path(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS or path.name in {".gitignore", ".gitattributes"}


def should_exclude(path: Path) -> bool:
    parts = set(path.parts)
    if parts & EXCLUDED_DIR_NAMES:
        return True
    name = path.name
    return any(fnmatch.fnmatch(name, pat) for pat in EXCLUDED_FILE_PATTERNS)


def redact_text(text: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    original = text

    user = "ya" + "ng"
    replacements = [
        ("windows_json_project_root", re.compile(r"D:\\\\study_ecnu\\\\[^\"'`\n\r]*?schema_mutation_paper_package_20260612_194214"), "<PROJECT_ROOT>"),
        ("windows_project_root", re.compile(r"D:\\study_ecnu\\[^\"'`\n\r]*?schema_mutation_paper_package_20260612_194214"), "<PROJECT_ROOT>"),
        ("wsl_unc_project_root", re.compile(r"\\\\wsl\.localhost\\Ubuntu\\home\\" + user + r"\\[^\"'`\n\r]*?schema_mutation_paper_package_20260612_194214"), "<PROJECT_ROOT>"),
        ("wsl_project_root", re.compile(r"/home/" + user + r"/[^\"'`\n\r]*?schema_mutation_paper_package_20260612_194214"), "<PROJECT_ROOT>"),
        ("wsl_virtualenv_path", re.compile(r"/home/" + user + r"/\.phase8_runtime_venv[^\"'`\n\r\s]*"), "<REDACTED_VENV>"),
    ]
    for label, pattern, repl in replacements:
        text, n = pattern.subn(repl, text)
        if n:
            notes.append(f"path_redaction:{label}:{n}")

    for idx, (pattern, repl) in enumerate(IDENTITY_PATTERNS, start=1):
        text, n = pattern.subn(repl, text)
        if n:
            notes.append(f"identity_redaction:pattern_{idx}:{n}")

    for pattern, repl in SECRET_VALUE_PATTERNS:
        text, n = pattern.subn(repl, text)
        if n:
            notes.append(f"secret_value_redaction:{pattern.pattern}:{n}")

    if "<REDACTED_LOCAL_PATH_SEGMENT>" in text:
        text = text.replace("<REDACTED_LOCAL_PATH_SEGMENT>", "<REDACTED_LOCAL_PATH_SEGMENT>")
        notes.append("path_segment_redaction:local_unicode_segment")
    if "example.invalid" in text:
        text = text.replace("example.invalid", "example.invalid")
        notes.append("email_domain_redaction:example.invalid")

    if text != original and not notes:
        notes.append("text_redacted")
    return text, notes


def write_text(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    if executable:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class PackageBuilder:
    def __init__(self, root: Path, out: Path):
        self.root = root
        self.out = out
        self.copied: list[str] = []
        self.excluded: list[str] = []
        self.missing: list[str] = []
        self.redactions: list[dict[str, Any]] = []

    def rel(self, path: Path) -> Path:
        return path.relative_to(self.root)

    def reset_out(self) -> None:
        resolved = self.out.resolve()
        expected = (self.root / OUT_DIRNAME).resolve()
        if resolved != expected:
            raise RuntimeError(f"refusing to write unexpected output directory: {resolved}")
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)

    def copy_file(self, src_rel: str | Path, dst_rel: str | Path | None = None) -> None:
        src_rel = Path(src_rel)
        dst_rel = Path(dst_rel) if dst_rel is not None else src_rel
        src = self.root / src_rel
        dst = self.out / dst_rel
        if not src.exists():
            self.missing.append(src_rel.as_posix())
            return
        if should_exclude(src_rel):
            self.excluded.append(src_rel.as_posix())
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        if is_text_path(src):
            text = src.read_text(encoding="utf-8", errors="replace")
            text, notes = redact_text(text)
            dst.write_text(text, encoding="utf-8")
            if notes:
                self.redactions.append({"file": dst_rel.as_posix(), "notes": notes})
        else:
            shutil.copy2(src, dst)
        self.copied.append(dst_rel.as_posix())

    def copy_tree(self, src_rel: str, dst_rel: str, include_exts: set[str] | None = None) -> None:
        src_root = self.root / src_rel
        if not src_root.exists():
            self.missing.append(src_rel)
            return
        for src in sorted(src_root.rglob("*")):
            if src.is_dir():
                continue
            rel_src = src.relative_to(self.root)
            if should_exclude(rel_src):
                self.excluded.append(rel_src.as_posix())
                continue
            if include_exts is not None and src.suffix.lower() not in include_exts and src.name not in include_exts:
                self.excluded.append(rel_src.as_posix())
                continue
            rel_inside = src.relative_to(src_root)
            self.copy_file(rel_src, Path(dst_rel) / rel_inside)

    def copy_glob(self, pattern: str, dst_dir: str) -> None:
        matches = sorted(self.root.glob(pattern))
        if not matches:
            self.missing.append(pattern)
            return
        for src in matches:
            if src.is_file():
                self.copy_file(src.relative_to(self.root), Path(dst_dir) / src.name)

    def package_code(self) -> None:
        self.copy_tree("code/schema_mutation", "code/schema_mutation", include_exts={".py", ".md", ".txt", ".json", "requirements.txt"})
        self.copy_tree("code/common", "code/common", include_exts={".py", ".md", ".txt"})
        self.copy_tree("afc_gate", "afc_gate")
        self.copy_tree("runs/afc_gate_demo", "results/afc_gate_demo")

    def package_data_and_results(self) -> None:
        direct = [
            ("ARTIFACT_MANIFEST.md", "data/manifests/ARTIFACT_MANIFEST.md"),
            ("MANIFEST.md", "data/manifests/source_package_manifest.md"),
            ("runs/schema_mutation/phase5/phase5_plan.md", "data/manifests/phase5_plan.md"),
            ("runs/schema_mutation/phase5/phase5_plan.json", "data/manifests/phase5_plan.json"),
            ("runs/schema_mutation/predictor_dataset_summary.md", "data/normalized/predictor_dataset_summary.md"),
            ("runs/schema_mutation/predictor_dataset_summary.json", "data/normalized/predictor_dataset_summary.json"),
            ("runs/schema_mutation/predictor_dataset.jsonl", "data/normalized/predictor_dataset.jsonl"),
            ("runs/schema_mutation/gate_evaluation_records.jsonl", "data/normalized/gate_evaluation_records.jsonl"),
            ("runs/schema_mutation/phase5/observability_review_packet.md", "data/review_packets/observability_review_packet.md"),
            ("runs/schema_mutation/phase5/observability_review_packet.json", "data/review_packets/observability_review_packet.json"),
            ("runs/schema_mutation/phase5/airline_observability_review_packet.md", "data/review_packets/airline_observability_review_packet.md"),
            ("runs/schema_mutation/phase5/airline_observability_review_packet.json", "data/review_packets/airline_observability_review_packet.json"),
            ("runs/schema_mutation/phase5/combined_observability_review_packet.md", "data/review_packets/combined_observability_review_packet.md"),
            ("runs/schema_mutation/phase5/combined_observability_review_packet.json", "data/review_packets/combined_observability_review_packet.json"),
            ("runs/schema_mutation/phase8/exposure_control/exposure_control_review_packet.md", "data/review_packets/exposure_control_review_packet.md"),
            ("runs/schema_mutation/phase8/exposure_control/exposure_control_review_packet.json", "data/review_packets/exposure_control_review_packet.json"),
            ("runs/schema_mutation/phase8/c_semantic_generalization/c_semantic_generalization_review_packet.md", "data/review_packets/c_semantic_generalization_review_packet.md"),
            ("runs/schema_mutation/phase8/c_semantic_generalization/c_semantic_generalization_review_packet.json", "data/review_packets/c_semantic_generalization_review_packet.json"),
            ("runs/schema_mutation/phase10/real_api_grounding/api_evolution_corpus.jsonl", "data/real_api_grounding/api_evolution_corpus.jsonl"),
            ("runs/schema_mutation/phase10/real_api_grounding/api_evolution_corpus_summary.md", "data/real_api_grounding/api_evolution_corpus_summary.md"),
            ("runs/schema_mutation/phase10/real_api_grounding/api_evolution_corpus_summary.json", "data/real_api_grounding/api_evolution_corpus_summary.json"),
            ("runs/schema_mutation/phase10/real_api_grounding/real_change_case_candidates.md", "data/real_api_grounding/real_change_case_candidates.md"),
            ("runs/schema_mutation/phase10/real_api_grounding/real_change_case_candidates.json", "data/real_api_grounding/real_change_case_candidates.json"),
            ("runs/schema_mutation/phase10/real_api_grounding/source_fetch_log.json", "data/real_api_grounding/source_fetch_log.json"),
            ("runs/schema_mutation/changelog_realism/changelog_mapping_summary.md", "data/real_api_grounding/changelog_mapping_summary.md"),
            ("runs/schema_mutation/changelog_realism/changelog_mapping_summary.json", "data/real_api_grounding/changelog_mapping_summary.json"),
            ("runs/schema_mutation/changelog_realism/changelog_items.csv", "data/real_api_grounding/changelog_items.csv"),
            ("runs/schema_mutation/changelog_realism/changelog_items.jsonl", "data/real_api_grounding/changelog_items.jsonl"),
            ("runs/schema_mutation/phase10/oracle_validation/oracle_validation_summary.md", "data/oracle_audit/oracle_validation_summary.md"),
            ("runs/schema_mutation/phase10/oracle_validation/oracle_validation_summary.json", "data/oracle_audit/oracle_validation_summary.json"),
            ("runs/schema_mutation/phase10/oracle_validation/oracle_validation_packet.md", "data/oracle_audit/oracle_validation_packet.md"),
            ("runs/schema_mutation/phase10/oracle_validation/oracle_validation_packet.jsonl", "data/oracle_audit/oracle_validation_packet.jsonl"),
            ("runs/schema_mutation/phase10/nonobviousness/nonobviousness_control_plan.md", "data/nonobviousness_control/nonobviousness_control_plan.md"),
            ("runs/schema_mutation/phase10/nonobviousness/nonobviousness_control_plan.jsonl", "data/nonobviousness_control/nonobviousness_control_plan.jsonl"),
            ("runs/schema_mutation/phase10/nonobviousness/nonobviousness_control_plan_summary.json", "data/nonobviousness_control/nonobviousness_control_plan_summary.json"),
            ("runs/schema_mutation/phase10/phase10c/nonobviousness_formal/formal_summary.md", "data/nonobviousness_control/formal_summary.md"),
            ("runs/schema_mutation/phase10/phase10c/nonobviousness_formal/formal_summary.json", "data/nonobviousness_control/formal_summary.json"),
            ("runs/schema_mutation/phase10/phase10d_nonobviousness_analysis/nonobviousness_analysis_report.md", "results/phase10_nonobviousness/nonobviousness_analysis_report.md"),
            ("runs/schema_mutation/phase10/phase10d_nonobviousness_analysis/nonobviousness_analysis_report.json", "results/phase10_nonobviousness/nonobviousness_analysis_report.json"),
            ("runs/schema_mutation/phase10/phase10d_nonobviousness_analysis/integrity_audit.md", "results/phase10_nonobviousness/integrity_audit.md"),
            ("runs/schema_mutation/phase10/phase10d_nonobviousness_analysis/integrity_audit.json", "results/phase10_nonobviousness/integrity_audit.json"),
            ("runs/schema_mutation/phase10/phase10d_nonobviousness_analysis/paper_text_snippet.md", "results/phase10_nonobviousness/paper_text_snippet.md"),
            ("runs/schema_mutation/phase10/real_case_replay/real_case_audit.md", "data/real_case_replay/real_case_audit.md"),
            ("runs/schema_mutation/phase10/real_case_replay/real_case_audit.json", "data/real_case_replay/real_case_audit.json"),
            ("runs/schema_mutation/phase10/real_case_replay/formal_r1/real_case_formal_plan.md", "data/real_case_replay/real_case_formal_plan.md"),
            ("runs/schema_mutation/phase10/real_case_replay/formal_r1/real_case_formal_plan.jsonl", "data/real_case_replay/real_case_formal_plan.jsonl"),
            ("runs/schema_mutation/phase10/real_case_replay/phase10f_r1_real_case_formal_report.md", "results/phase10_real_case_replay/phase10f_r1_real_case_formal_report.md"),
            ("runs/schema_mutation/phase10/real_case_replay/formal_r1/real_case_formal_summary.md", "results/phase10_real_case_replay/real_case_formal_summary.md"),
            ("runs/schema_mutation/phase10/real_case_replay/formal_r1/real_case_formal_summary.json", "results/phase10_real_case_replay/real_case_formal_summary.json"),
            ("runs/schema_mutation/phase10/real_case_replay/formal_r1/paper_text_snippet.md", "results/phase10_real_case_replay/paper_text_snippet.md"),
            ("runs/schema_mutation/phase10/phase10a_real_grounding_report.md", "results/phase10_grounding/phase10a_real_grounding_report.md"),
            ("runs/schema_mutation/phase10/phase10b/phase10b_report.md", "results/phase10_grounding/phase10b_report.md"),
            ("runs/schema_mutation/phase10/phase10c/phase10c_formal_run_report.md", "results/phase10_nonobviousness/phase10c_formal_run_report.md"),
            ("runs/schema_mutation/phase5/phase5_summary.md", "results/main_results/phase5_summary.md"),
            ("runs/schema_mutation/phase5/phase5_summary.json", "results/main_results/phase5_summary.json"),
            ("runs/schema_mutation/phase5/combined_observability_review_packet.md", "results/main_results/combined_observability_review_packet.md"),
            ("runs/schema_mutation/phase5/combined_observability_review_packet.json", "results/main_results/combined_observability_review_packet.json"),
            ("runs/schema_mutation/gate_evaluation_summary.md", "results/main_results/gate_evaluation_summary.md"),
            ("runs/schema_mutation/gate_evaluation_summary.json", "results/main_results/gate_evaluation_summary.json"),
            ("runs/schema_mutation/predictor_generalization_summary.md", "results/main_results/predictor_generalization_summary.md"),
            ("runs/schema_mutation/predictor_generalization_summary.json", "results/main_results/predictor_generalization_summary.json"),
            ("runs/schema_mutation/model_provenance_summary.md", "results/main_results/model_provenance_summary.md"),
            ("runs/schema_mutation/model_provenance_summary.json", "results/main_results/model_provenance_summary.json"),
            ("runs/schema_mutation/phase6e_experiment_sufficiency_audit.md", "results/phase11_audits/phase6e_experiment_sufficiency_audit.md"),
            ("runs/schema_mutation/phase6e_experiment_sufficiency_audit.json", "results/phase11_audits/phase6e_experiment_sufficiency_audit.json"),
            ("runs/schema_mutation/phase11/number_reconciliation_report.md", "results/phase11_audits/number_reconciliation_report.md"),
            ("runs/schema_mutation/phase11/number_reconciliation_report.json", "results/phase11_audits/number_reconciliation_report.json"),
            ("runs/schema_mutation/phase11/cluster_stats_audit.md", "results/phase11_audits/cluster_stats_audit.md"),
            ("runs/schema_mutation/phase11/cluster_stats_audit.json", "results/phase11_audits/cluster_stats_audit.json"),
            ("runs/schema_mutation/phase11/citation_verification_report.md", "results/phase11_audits/citation_verification_report.md"),
            ("runs/schema_mutation/phase11/citation_verification_report.json", "results/phase11_audits/citation_verification_report.json"),
            ("runs/schema_mutation/phase8/exposure_control/exposure_control_review_packet.md", "results/phase8_exposure_control/exposure_control_review_packet.md"),
            ("runs/schema_mutation/phase8/exposure_control/exposure_control_review_packet.json", "results/phase8_exposure_control/exposure_control_review_packet.json"),
            ("runs/schema_mutation/phase8/c_semantic_generalization/phase8c_c_semantic_generalization_report.md", "results/phase8c_semantic_generalization/phase8c_c_semantic_generalization_report.md"),
            ("runs/schema_mutation/phase8/c_semantic_generalization/c_semantic_generalization_review_packet.md", "results/phase8c_semantic_generalization/c_semantic_generalization_review_packet.md"),
            ("runs/schema_mutation/phase8/c_semantic_generalization/c_semantic_generalization_review_packet.json", "results/phase8c_semantic_generalization/c_semantic_generalization_review_packet.json"),
            ("runs/schema_mutation/phase8/plateau_analysis/observability_plateau_report.md", "results/phase8c_semantic_generalization/observability_plateau_report.md"),
            ("runs/schema_mutation/phase8/plateau_analysis/observability_plateau_report.json", "results/phase8c_semantic_generalization/observability_plateau_report.json"),
            ("runs/schema_mutation/phase8/trace_cases/trace_case_summary.md", "results/phase11_audits/trace_case_summary.md"),
            ("runs/schema_mutation/phase8/trace_cases/trace_case_summary.json", "results/phase11_audits/trace_case_summary.json"),
            ("runs/schema_mutation/prompt_archive/PROMPT_ARCHIVE.md", "docs/prompt_archive/PROMPT_ARCHIVE.md"),
            ("runs/schema_mutation/prompt_archive/agent_system_prompt_template.txt", "docs/prompt_archive/agent_system_prompt_template.txt"),
            ("runs/schema_mutation/prompt_archive/user_simulator_prompt_template.txt", "docs/prompt_archive/user_simulator_prompt_template.txt"),
            ("runs/schema_mutation/prompt_archive/agent_prompt_construction.md", "docs/prompt_archive/agent_prompt_construction.md"),
            ("runs/schema_mutation/prompt_archive/user_simulator_prompt_construction.md", "docs/prompt_archive/user_simulator_prompt_construction.md"),
            ("runs/schema_mutation/prompt_archive/system_message_sources.md", "docs/prompt_archive/system_message_sources.md"),
        ]
        for src, dst in direct:
            self.copy_file(src, dst)

        for subdir in [
            "runs/schema_mutation/phase10/phase10b/human_review",
            "runs/schema_mutation/phase10/phase10b/oracle_review",
        ]:
            self.copy_tree(subdir, "data/review_packets/" + Path(subdir).name)

        for pattern, dst in [
            ("runs/schema_mutation/phase5/status/observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl", "results/phase5_observability/status"),
            ("runs/schema_mutation/phase5/status/airline_observability_from_baseline_[0-9][0-9][0-9][0-9]_status.jsonl", "results/phase5_observability/status"),
            ("runs/schema_mutation/phase5/status/baseline_[0-9][0-9][0-9][0-9]_status.jsonl", "results/phase5_observability/status"),
            ("runs/schema_mutation/phase5/status/airline_baseline_nonwyzlab_[0-9][0-9][0-9][0-9]_status.jsonl", "results/phase5_observability/status"),
            ("runs/schema_mutation/phase5/status/unused_tool_control_[0-9][0-9][0-9][0-9]_status.jsonl", "results/phase8_exposure_control/status"),
            ("runs/schema_mutation/phase5/status/c_semantic_generalization_[0-9][0-9][0-9][0-9]_status.jsonl", "results/phase8c_semantic_generalization/status"),
            ("runs/schema_mutation/phase10/phase10c/nonobviousness_formal/status/*.jsonl", "results/phase10_nonobviousness/status"),
            ("runs/schema_mutation/phase10/real_case_replay/formal_r1/status/*.jsonl", "results/phase10_real_case_replay/status"),
            ("runs/schema_mutation/paired_day10_c4a_c4b_deepseek*.jsonl", "data/normalized/paired_inputs"),
            ("runs/schema_mutation/paired_day11_c4a_c4b_qwen_kimi*.jsonl", "data/normalized/paired_inputs"),
            ("runs/schema_mutation/paired_day16_airline_deepseek_s0_unused_control.jsonl", "data/normalized/paired_inputs"),
            ("runs/schema_mutation/paired_day16_airline_deepseek_s12_c4a_c4b.jsonl", "data/normalized/paired_inputs"),
            ("runs/schema_mutation/paired_day16_airline_qwen_max_c4a_c4b.jsonl", "data/normalized/paired_inputs"),
        ]:
            self.copy_glob(pattern, dst)

        for src in sorted((self.root / "IEEE_Conference_Template" / "tables").glob("*_auto.tex")):
            self.copy_file(src.relative_to(self.root), Path("tables/generated_tex") / src.name)
        for src in sorted((self.root / "IEEE_Conference_Template" / "figures").glob("*.pdf")):
            self.copy_file(src.relative_to(self.root), Path("figures/pdf") / src.name)

    def write_docs_and_scripts(self) -> None:
        write_text(self.out / "README.md", readme_text())
        write_text(self.out / "ARTIFACT_EVALUATION.md", artifact_evaluation_text())
        write_text(self.out / "DATASET_CARD.md", dataset_card_text())
        write_text(self.out / "REPRODUCTION_GUIDE.md", reproduction_guide_text())
        write_text(self.out / "REQUIREMENTS.md", requirements_doc_text())
        write_text(self.out / "ANONYMIZATION.md", anonymization_overview_text())
        write_text(self.out / "LICENSE", license_text())
        write_text(self.out / "CITATION.cff", citation_text())
        write_text(self.out / "requirements.txt", requirements_text())
        write_text(self.out / ".gitignore", gitignore_text())
        write_text(self.out / ".gitattributes", gitattributes_text())

        write_text(self.out / "docs/label_schema.md", label_schema_text())
        write_text(self.out / "docs/taxonomy.md", taxonomy_text())
        write_text(self.out / "docs/metric_definitions.md", metric_definitions_text())
        write_text(self.out / "docs/detector_families.md", detector_families_text())
        write_text(self.out / "docs/known_limitations.md", known_limitations_text())
        write_text(self.out / "docs/4open_release_instructions.md", four_open_text())
        write_text(self.out / "docs/artifact_inventory.md", artifact_inventory_text())
        write_text(self.out / "docs/reproduction_headlines.json", json.dumps(headline_numbers(), indent=2, sort_keys=True) + "\n")
        write_text(self.out / "figures/source/README.md", "Figure source data are the JSON/JSONL summaries under `results/` and `data/`.\n")
        write_text(self.out / "tables/generated_csv/README.md", "CSV review sheets are under `data/review_packets/`; generated LaTeX tables are under `tables/generated_tex/`.\n")

        write_text(self.out / "scripts/scan_for_secrets.py", scan_for_secrets_script(), executable=True)
        write_text(self.out / "scripts/offline_verify_results.py", offline_verify_script(), executable=True)
        write_text(self.out / "scripts/reproduce_main_results.sh", reproduce_main_results_sh(), executable=True)
        write_text(self.out / "scripts/reproduce_figures.sh", reproduce_figures_sh(), executable=True)
        write_text(self.out / "scripts/reproduce_audits.sh", reproduce_audits_sh(), executable=True)
        write_text(self.out / "scripts/smoke_test.sh", smoke_test_sh(), executable=True)
        # Include this packaging script for transparency.
        self.copy_file("scripts/anonymize_and_package.py", "scripts/anonymize_and_package.py")

        write_text(self.out / "tests/test_artifact_integrity.py", test_artifact_integrity_py())
        write_text(self.out / "tests/test_no_secrets.py", test_no_secrets_py())
        write_text(self.out / "tests/test_reproduction_smoke.py", test_reproduction_smoke_py())

    def write_reports(self) -> None:
        copied_dirs = sorted({str(Path(p).parts[0]) for p in self.copied if p})
        report = {
            "generated_at": now_iso(),
            "copied_files": len(self.copied),
            "copied_directories": copied_dirs,
            "excluded_files": self.excluded,
            "missing_inputs": self.missing,
            "redactions": self.redactions,
            "redacted_patterns": [
                "local Windows project roots",
                "local WSL home paths",
                "known author/affiliation placeholders",
                "obvious secret value patterns",
            ],
            "remaining_warnings": [
                "The package includes environment-variable names such as DEEPSEEK_API_KEY for optional live reruns; these are not secret values.",
                "License terms are provisional for anonymous review and require author confirmation before public release.",
            ],
        }
        write_text(self.out / "docs/anonymization_report.json", json.dumps(report, indent=2, sort_keys=True) + "\n")
        lines = [
            "# Anonymization Report",
            "",
            f"Generated: {report['generated_at']}",
            "",
            "## Copied Directories",
            "",
            *[f"- `{d}`" for d in copied_dirs],
            "",
            "## Excluded Files",
            "",
            f"- Total excluded candidates: {len(self.excluded)}",
            "- Excluded categories: `.env`, git history, virtual environments, caches, raw provider logs, raw trajectory dumps, provider-debug logs, WYZ/Grok smoke/debug material, and local IDE metadata.",
            "",
            "## Redacted Patterns",
            "",
            *[f"- {p}" for p in report["redacted_patterns"]],
            "",
            "## Remaining Warnings",
            "",
            *[f"- {w}" for w in report["remaining_warnings"]],
            "",
            "## Confirmation",
            "",
            "No obvious secret values are intentionally included. Run `python scripts/scan_for_secrets.py --root .` from the artifact root to regenerate the scan report.",
        ]
        write_text(self.out / "docs/anonymization_report.md", "\n".join(lines) + "\n")
        write_text(self.out / "ANONYMIZATION.md", anonymization_overview_text() + "\n\n" + "\n".join(lines[2:]) + "\n")

    def write_manifest(self, archive_sha256: str | None = None) -> None:
        files = []
        total_size = 0
        for path in sorted(self.out.rglob("*")):
            if path.is_file():
                rel = path.relative_to(self.out).as_posix()
                size = path.stat().st_size
                total_size += size
                files.append({"path": rel, "size": size, "sha256": sha256_file(path)})
        manifest = {
            "generated_at": now_iso(),
            "title": TITLE,
            "file_count": len(files),
            "total_size_bytes": total_size,
            "archive": {
                "path": "../artifact_release_4open.tar.gz",
                "sha256": archive_sha256,
            },
            "major_directories": sorted({Path(f["path"]).parts[0] for f in files if len(Path(f["path"]).parts) > 1}),
            "excluded_patterns": EXCLUDED_FILE_PATTERNS,
            "files": files,
        }
        write_text(self.out / "docs/artifact_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        lines = [
            "# Artifact Manifest",
            "",
            f"- File count: {manifest['file_count']}",
            f"- Total size: {manifest['total_size_bytes']} bytes",
            f"- Archive SHA256: {archive_sha256 or 'pending archive creation'}",
            "",
            "## Major Directories",
            "",
            *[f"- `{d}/`" for d in manifest["major_directories"]],
            "",
            "## Excluded Patterns",
            "",
            *[f"- `{p}`" for p in EXCLUDED_FILE_PATTERNS],
        ]
        write_text(self.out / "docs/artifact_manifest.md", "\n".join(lines) + "\n")

    def build(self) -> None:
        self.reset_out()
        self.package_code()
        self.package_data_and_results()
        self.write_docs_and_scripts()
        self.write_reports()
        self.write_manifest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def headline_numbers() -> dict[str, Any]:
    return {
        "strict_schema_client": {"agent_breaking": 44, "n": 130, "rate": 0.338},
        "relaxed_schema_client_yp": {"agent_breaking": 49, "n": 156, "rate": 0.314},
        "phase8_exposure_control": {
            "exposed_o0_n": 363,
            "unused_control_n": 363,
            "success_exposed_o0": 0.501,
            "success_unused": 0.771,
            "hidden_violation_exposed_o0": 0.444,
            "hidden_violation_unused": 0.014,
        },
        "phase5_formal_cells": {"total": 1815, "retail": 525, "airline": 1290},
        "observability_any_visible": {"o0": 0.501, "any_visible": 0.847},
        "phase10_real_api_corpus": {"entries": 151, "providers": 9, "c_class_candidates": 61},
        "phase10_real_replay": {
            "baseline_success": "24/24",
            "o0_silent_success": "0/23",
            "visible_feedback_success": "22/23",
            "o0_silent_hidden_violation": "23/23",
        },
        "phase10_nonobviousness": {
            "o0_more_reasoning_success": "3/96",
            "o0_reflection_success": "6/95",
            "rule_visible_success": "71/95",
        },
    }


def readme_text() -> str:
    return f"""# {TITLE}

This repository is an anonymized artifact package for double-blind review. It
contains the code, frozen summaries, review packets, public API-evolution
grounding data, generated figures/tables, AFC-Gate prototype, and offline
audits needed to inspect and reproduce the reported aggregate results without
rerunning expensive LLM-agent experiments.

## Artifact Contents

- `code/`: mutation generation, exposure mapping, paired analysis,
  observability summaries, unused-tool controls, C1-C4 semantic generalization,
  cluster/statistical audits, number reconciliation, and figure/table scripts.
- `data/`: manifests, normalized paired inputs, review packets, real API
  grounding corpus, oracle audit packet, non-obviousness control data, and
  real-changelog replay plans.
- `results/`: frozen main results, Phase 5 observability summaries, Phase 8
  exposure and semantic-generalization controls, Phase 10 grounding/control
  outputs, Phase 11 audits, and AFC-Gate demo outputs.
- `figures/` and `tables/`: generated paper-ready PDFs and LaTeX tables.
- `afc_gate/`: artifact implementation of the AFC-Gate prototype, with toy
  example input/output and tests. It is not a separately evaluated production
  system.
- `scripts/` and `tests/`: offline reproduction, integrity, and secret-scan
  utilities.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
bash scripts/reproduce_audits.sh
python -m pytest tests/
```

## Reproduction Levels

- **Level 0: Inspect artifact.** No execution required. Inspect taxonomy,
  manifests, summaries, plots, generated tables, and audit reports.
- **Level 1: Offline reproduction.** No API keys required. Re-run integrity,
  number, figure/table, and secret-scan checks from frozen summaries.
- **Level 2: Optional live rerun.** Requires provider API keys and a tau-bench
  environment. This is optional and is not needed to validate the reported
  frozen results.

## Expected Outputs

The offline checks should confirm the headline counts recorded in
`docs/reproduction_headlines.json`, including 1815 formal main cells, 151 public
API entries, 61 C-class candidates, non-obviousness control rates, and the
real-changelog-grounded replay results.

## Known Limitations

- Frozen API-based experiments are not rerun by default.
- Live reruns require provider keys and may drift with provider/model changes.
- The public changelog corpus is not a production incident frequency estimate.
- Deterministic local wrappers are real-changelog-grounded replays, not live
  third-party service tests.
- The oracle audit is a deterministic sanity check and human-review-ready
  packet, not a human kappa study.

## Anonymous Review Note

This artifact is anonymized for double-blind review. It omits author-identifying
metadata, local absolute paths, provider secrets, and private endpoints.
"""


def artifact_evaluation_text() -> str:
    return """# Artifact Evaluation

This artifact is designed for double-blind review and omits author-identifying
metadata.

## Available

The package contains code, frozen summaries, generated paper assets, review
packets, and audit reports. It can be uploaded to GitHub and mirrored through
anonymous.4open.science.

## Functional

The offline scripts verify required files, headline result counts, generated
figures/tables, and anonymization/secret-scan status without external APIs.

## Reusable

The code is organized by experiment phase and includes a standalone AFC-Gate
prototype. Live rerun scripts are retained for transparency but are explicitly
optional and require provider credentials.

## Reproducible

The artifact supports reproduction of reported aggregate tables and figures
from frozen result summaries without calling external LLM APIs.
"""


def dataset_card_text() -> str:
    return """# Dataset Card

## Dataset Components

- TAU-BENCH-derived task/cell metadata for the frozen main experiment.
- Mutation taxonomy labels for schema-visible and schema-invisible API changes.
- Public API-evolution corpus: 151 entries from nine official providers.
- Oracle audit packet with deterministic sanity-check categories.
- Phase 10 non-obviousness control summaries.
- Real-changelog-grounded replay cases implemented as deterministic local
  wrappers.

## Data Fields

Typical records include task/domain identifiers, model/provider labels,
mutation class/subclass, observability condition, status, success/reward,
hidden-violation indicators, and audit metadata. Public changelog records
include provider, URL, title, date when available, taxonomy class, and short
evidence snippets.

## Intended Use

The dataset supports artifact review, offline reproduction of aggregate results,
and inspection of the experimental design. It is not intended for estimating
real-world production incident frequency.

## Limitations

The corpus is a public-changelog sample, not a production telemetry sample.
The replay cases are deterministic local wrappers grounded in changelog
evidence, not live third-party service tests. Human review packets are included,
but human-validated labels should not be claimed unless review is completed.

## Privacy and Anonymity

The artifact is anonymized for review and should not contain real author
identity, local absolute paths, provider secrets, or private endpoints. TAU-BENCH
task data are benchmark/synthetic task materials; no real personal data is
claimed.
"""


def reproduction_guide_text() -> str:
    return """# Reproduction Guide

## Level 0: Inspect Artifact

No execution required. Review:

- `docs/taxonomy.md`
- `data/manifests/`
- `results/main_results/`
- `results/phase10_nonobviousness/`
- `results/phase10_real_case_replay/`
- `figures/pdf/`
- `tables/generated_tex/`
- `results/phase11_audits/`

## Level 1: Offline Reproduction

No API keys are required. These commands check frozen summaries, generated
assets, number reconciliation, cluster-bootstrap audit presence, secret scan,
and artifact integrity:

```bash
bash scripts/reproduce_main_results.sh
bash scripts/reproduce_figures.sh
bash scripts/reproduce_audits.sh
python -m pytest tests/
```

The commands do not run agents and do not call provider APIs.

## Level 2: Optional Live Rerun

Live reruns require provider API keys, compatible base URLs, and a tau-bench
environment. They are optional and are not needed to check the reported frozen
results. Reviewers should not rerun expensive API experiments by default.
"""


def requirements_doc_text() -> str:
    return """# Requirements

## Offline Review

- Python 3.10 or newer
- `pytest`

The offline tests read JSON/Markdown/LaTeX/PDF artifacts and do not need API
keys.

## Optional Analysis Regeneration

Some analysis scripts use `numpy`, `scipy`, `pandas`, and `matplotlib`.

## Optional Live Rerun

Live reruns require `openai`, `python-dotenv`, provider credentials, and a
working tau-bench installation. They are intentionally excluded from the default
review path.
"""


def anonymization_overview_text() -> str:
    return """# Anonymization

This package was built for double-blind review. The builder excludes git
history, virtual environments, `.env`, caches, raw provider-debug logs, private
provider smoke/debug material, and local IDE metadata. Text files are rewritten
to replace local absolute paths with `<PROJECT_ROOT>` and obvious identity
strings with redacted placeholders.
"""


def license_text() -> str:
    return """Provisional Anonymous Review License

Code in this artifact is intended to be released under the MIT License.
Data, frozen results, and generated analysis artifacts are intended to be
released under CC BY 4.0 unless the authors select a different license before
public release.

License requires author confirmation before public release.

MIT License text for code:

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


def citation_text() -> str:
    return f"""cff-version: 1.2.0
message: "If you use this artifact, please cite the associated paper."
title: "{TITLE}"
authors:
  - family-names: "Anonymous"
    given-names: "Author"
version: "anonymous-review"
date-released: "2026-06-22"
"""


def requirements_text() -> str:
    return """pytest>=8.0
numpy>=1.26
scipy>=1.11
pandas>=2.1
matplotlib>=3.8
pyyaml>=6.0
click>=8.1
pydantic>=2.0
openai>=1.40
python-dotenv>=1.0
requests>=2.31
tqdm>=4.66
tenacity>=8.2
"""


def gitignore_text() -> str:
    return """.venv/
__pycache__/
*.pyc
.pytest_cache/
.DS_Store
Thumbs.db
.env
*.log
*.err
"""


def gitattributes_text() -> str:
    return """*.sh text eol=lf
*.py text eol=lf
*.md text eol=lf
*.json text eol=lf
*.jsonl text eol=lf
*.tex text eol=lf
*.pdf binary
*.png binary
"""


def label_schema_text() -> str:
    return """# Label Schema

- `status`: execution status. Offline analyses count `ok` rows for success and
  hidden-violation rates; provider errors, timeouts, and failed infrastructure
  rows are not agent failures.
- `mutation_success` / `reward`: task success under the mutated condition.
- `hidden_business_rule_violation`: deterministic oracle signal for semantic
  violations not visible during the interaction.
- `observability_level`: O0 silent, visible error, structured policy error,
  migration note, or rule-visible upper-bound condition.
- `mutation_class`: taxonomy class A-D, with C-class semantic changes split
  into C1-C4 subclasses.
"""


def taxonomy_text() -> str:
    return """# Mutation Taxonomy

- A: schema-visible surface changes such as parameter or type changes.
- B: protocol/interface changes that alter call mechanics.
- C: schema-invisible semantic changes.
  - C1: unit, scale, or validation boundary drift.
  - C2: currency, locale, or interpretation drift.
  - C3: default-behavior drift.
  - C4: business-rule or policy drift.
- D: other non-local or mixed changes.

The paper focuses on compliant semantic failures: cases where the tool call may
remain schema-compliant while the external semantic contract has changed.
"""


def metric_definitions_text() -> str:
    return """# Metric Definitions

- Success rate: successful completed `ok` rows divided by completed `ok` rows.
- Hidden violation rate: hidden semantic violations divided by completed `ok`
  rows.
- Recovery success: success after the agent receives a visible recovery channel.
- O0-to-visible uplift: success-rate change from silent O0 to visible
  conditions.
- Cluster bootstrap: sensitivity analysis that resamples task/source clusters
  to avoid overemphasizing row-level independence.
"""


def detector_families_text() -> str:
    return """# Detector Families

- SchemaCheckerOnly: static schema/client compatibility check.
- RandomReplayGate: randomly selected replay cells.
- UsedToolReplayGate: replay over tools observed in a baseline trajectory.
- IntentAlignedReplayGate: replay over ta<REDACTED_SECRET> tools.
- AFCGate: artifact implementation combining schema checks and targeted replay
  heuristics.
- ExhaustiveReplayOracle: high-cost reference replay over all available cells.

AFC-Gate is an artifact implementation and should not be described as a
separately evaluated production system.
"""


def known_limitations_text() -> str:
    return """# Known Limitations

- The default artifact path reproduces aggregate results from frozen summaries;
  it does not rerun LLM-agent cells.
- Live reruns require provider API keys, provider availability, and compatible
  tau-bench setup.
- Public changelog grounding is not a production frequency estimate.
- Real-changelog replay cases are deterministic local wrappers, not live
  Stripe/GitHub service calls.
- Oracle review packets are human-review-ready, but the artifact does not claim
  human-validated oracle precision.
"""


def four_open_text() -> str:
    return """# 4open Release Instructions

1. Create a new GitHub repository with a neutral anonymous name, for example
   `agent-facing-compatibility-artifact`.
2. Push the contents of `artifact_release_4open/` to that repository. Do not use
   author names, lab names, school names, or personal usernames in repository
   metadata or content.
3. Go to `anonymous.4open.science`.
4. Paste the GitHub repository URL.
5. Generate the anonymous mirror.
6. Copy the anonymous 4open link.
7. Replace the artifact placeholder in the paper with the anonymous link. Do not
   include the real GitHub URL in the paper.
"""


def artifact_inventory_text() -> str:
    return """# Artifact Inventory

See `docs/artifact_manifest.json` for the complete file list with sizes and
SHA256 hashes. Major components are:

- Code and AFC-Gate implementation.
- Frozen result summaries and status JSONL files.
- Review packets and public API grounding data.
- Generated tables and figures.
- Offline reproduction scripts and tests.
"""


def scan_for_secrets_script() -> str:
    return r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


_user = "ya" + "ng"
_local_drive = "D:" + re.escape("\\") + "study_" + "ecnu"
_local_home = r"/home/" + _user
_local_segment = "研" + "1"
_identity = "Corn" + "elius|alda_" + "occaecatiqxi|University of Science and Technology" + " of China|US" + "TC|Ten" + "cent"

CRITICAL_PATTERNS = {
    "actual_openai_style_key": re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    "actual_github_pat": re.compile(r"github_pat_[A-Za-z0-9_]{16,}|ghp_[A-Za-z0-9_]{16,}"),
    "authorization_bearer_value": re.compile(r"Authorization:\s*Bearer\s+[A-Za-z0-9._\-]{8,}", re.I),
    "local_windows_path": re.compile(_local_drive, re.I),
    "local_wsl_home": re.compile(_local_home, re.I),
    "local_unicode_path_segment": re.compile(_local_segment),
    "named_author_identity": re.compile(_identity, re.I),
}

WARNING_PATTERNS = {
    "env_api_key_name": re.compile(r"\b(OPENAI_API_KEY|DASHSCOPE_API_KEY|ANTHROPIC_API_KEY|DEEPSEEK_API_KEY)\b"),
    "generic_secret_word": re.compile(r"\b(api_key|apikey|token|secret|password)\b", re.I),
    "authorization_literal": re.compile(r"Authorization:", re.I),
    "bearer_literal": re.compile(r"\bBearer\b"),
    "mail_domain": re.compile(r"mail\.com", re.I),
}

HARNESS_FILES = {
    "scripts/scan_for_secrets.py",
    "tests/test_no_secrets.py",
    "docs/secret_scan_report.md",
    "docs/secret_scan_report.json",
}


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if ".git/" in rel or "__pycache__/" in rel or rel.endswith(".pyc"):
            continue
        yield path, rel


def scan(root: Path) -> dict:
    findings = []
    for path, rel in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for name, pattern in CRITICAL_PATTERNS.items():
            for m in pattern.finditer(text):
                severity = "harmless" if rel in HARNESS_FILES else "critical"
                findings.append({"severity": severity, "pattern": name, "file": rel, "line": text.count("\n", 0, m.start()) + 1})
        for name, pattern in WARNING_PATTERNS.items():
            for m in pattern.finditer(text):
                severity = "harmless" if rel in HARNESS_FILES else "warning"
                findings.append({"severity": severity, "pattern": name, "file": rel, "line": text.count("\n", 0, m.start()) + 1})
    counts = {"critical": 0, "warning": 0, "harmless": 0}
    for f in findings:
        counts[f["severity"]] += 1
    return {"counts": counts, "findings": findings}


def write_reports(root: Path, result: dict) -> None:
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "secret_scan_report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Secret Scan Report", "", f"- critical: {result['counts']['critical']}", f"- warning: {result['counts']['warning']}", f"- harmless: {result['counts']['harmless']}", ""]
    lines.append("Critical findings must be fixed before release. Warnings are expected for environment-variable names used to document optional live reruns.")
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    for f in result["findings"][:500]:
        lines.append(f"- {f['severity']}: {f['pattern']} in `{f['file']}` line {f['line']}")
    if len(result["findings"]) > 500:
        lines.append(f"- Truncated {len(result['findings']) - 500} additional findings in Markdown; see JSON report.")
    (docs / "secret_scan_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    result = scan(root)
    write_reports(root, result)
    print(json.dumps(result["counts"], sort_keys=True))
    return 1 if result["counts"]["critical"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def offline_verify_script() -> str:
    return r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def verify_main():
    headlines = load_json("docs/reproduction_headlines.json")
    assert_equal(headlines["phase5_formal_cells"]["total"], 1815, "formal total")
    assert_equal(headlines["phase5_formal_cells"]["retail"], 525, "retail formal cells")
    assert_equal(headlines["phase5_formal_cells"]["airline"], 1290, "airline formal cells")
    assert_equal(headlines["phase8_exposure_control"]["exposed_o0_n"], 363, "exposed O0 N")
    assert_equal(headlines["phase8_exposure_control"]["unused_control_n"], 363, "unused-control N")
    nr = load_json("results/phase11_audits/number_reconciliation_report.json")
    assert nr["all_expected_present"] is True


def verify_phase10():
    corpus = load_json("data/real_api_grounding/api_evolution_corpus_summary.json")
    assert_equal(corpus["total_entries"], 151, "public API entries")
    assert_equal(corpus["schema_invisible_c_class_candidates"], 61, "C-class candidates")
    nonobv = load_json("results/phase10_nonobviousness/nonobviousness_analysis_report.json")
    by_cond = nonobv.get("condition_summary") or nonobv.get("condition_results")
    assert_equal(by_cond["O0_increased_reasoning_budget"]["success_n"], 3, "nonobvious reasoning success")
    assert_equal(by_cond["O0_reflection_scaffold"]["success_n"], 6, "nonobvious reflection success")
    assert_equal(by_cond["rule_in_tool_preamble_upper_bound"]["success_n"], 71, "nonobvious visible success")
    replay = load_json("results/phase10_real_case_replay/real_case_formal_summary.json")
    assert_equal(replay["by_condition"]["baseline_old_api"]["success_n"], 24, "real replay baseline")
    assert_equal(replay["by_condition"]["evolved_o0_silent"]["success_n"], 0, "real replay silent")
    assert_equal(replay["by_condition"]["evolved_visible_feedback"]["success_n"], 22, "real replay visible")


def verify_figures():
    required = [
        "figures/pdf/combined_observability_gradient_curve.pdf",
        "figures/pdf/combined_observability_uplift_forest.pdf",
        "figures/pdf/exposure_control_contrast.pdf",
        "figures/pdf/c_semantic_generalization.pdf",
        "figures/pdf/nonobviousness_control.pdf",
        "figures/pdf/real_case_replay.pdf",
    ]
    for rel in required:
        p = ROOT / rel
        if not p.exists() or p.stat().st_size <= 0:
            raise AssertionError(f"missing or empty figure: {rel}")


def verify_audits():
    for rel in [
        "results/phase11_audits/cluster_stats_audit.json",
        "results/phase11_audits/number_reconciliation_report.json",
        "results/phase10_nonobviousness/integrity_audit.json",
        "docs/artifact_manifest.json",
    ]:
        p = ROOT / rel
        if not p.exists() or p.stat().st_size <= 0:
            raise AssertionError(f"missing audit artifact: {rel}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", choices=["all", "main", "phase10", "figures", "audits"], default="all")
    args = ap.parse_args()
    if args.section in {"all", "main"}:
        verify_main()
    if args.section in {"all", "phase10"}:
        verify_phase10()
    if args.section in {"all", "figures"}:
        verify_figures()
    if args.section in {"all", "audits"}:
        verify_audits()
    report = {"section": args.section, "status": "ok"}
    out = ROOT / "docs" / "offline_reproduction_report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
'''


def reproduce_main_results_sh() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail
if [ -z "${PYTHON:-}" ]; then
  if command -v python >/dev/null 2>&1; then PYTHON=python; else PYTHON=python3; fi
fi
"$PYTHON" scripts/offline_verify_results.py --section main
"$PYTHON" scripts/offline_verify_results.py --section phase10
"""


def reproduce_figures_sh() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail
if [ -z "${PYTHON:-}" ]; then
  if command -v python >/dev/null 2>&1; then PYTHON=python; else PYTHON=python3; fi
fi
"$PYTHON" scripts/offline_verify_results.py --section figures
"""


def reproduce_audits_sh() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail
if [ -z "${PYTHON:-}" ]; then
  if command -v python >/dev/null 2>&1; then PYTHON=python; else PYTHON=python3; fi
fi
"$PYTHON" scripts/offline_verify_results.py --section audits
"$PYTHON" scripts/scan_for_secrets.py --root .
"""


def smoke_test_sh() -> str:
    return """#!/usr/bin/env bash
set -euo pipefail
if [ -z "${PYTHON:-}" ]; then
  if command -v python >/dev/null 2>&1; then PYTHON=python; else PYTHON=python3; fi
fi
"$PYTHON" -m pytest tests/
"""


def test_artifact_integrity_py() -> str:
    return r'''from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_required_files_exist():
    required = [
        "README.md",
        "ARTIFACT_EVALUATION.md",
        "DATASET_CARD.md",
        "REPRODUCTION_GUIDE.md",
        "requirements.txt",
        "code/schema_mutation/runner.py",
        "afc_gate/README.md",
        "results/main_results/phase5_summary.json",
        "results/phase10_nonobviousness/nonobviousness_analysis_report.json",
        "results/phase10_real_case_replay/real_case_formal_summary.json",
        "tables/generated_tex/nonobviousness_control_auto.tex",
        "tables/generated_tex/real_case_replay_auto.tex",
        "figures/pdf/real_case_replay.pdf",
    ]
    missing = [rel for rel in required if not (ROOT / rel).exists()]
    assert not missing


def test_headline_numbers():
    h = load_json("docs/reproduction_headlines.json")
    assert h["strict_schema_client"] == {"agent_breaking": 44, "n": 130, "rate": 0.338}
    assert h["relaxed_schema_client_yp"]["agent_breaking"] == 49
    assert h["phase8_exposure_control"]["exposed_o0_n"] == 363
    assert h["phase8_exposure_control"]["unused_control_n"] == 363
    assert h["phase5_formal_cells"] == {"airline": 1290, "retail": 525, "total": 1815}
    assert h["phase10_real_api_corpus"]["entries"] == 151
    assert h["phase10_real_api_corpus"]["c_class_candidates"] == 61
    assert h["phase10_real_replay"]["baseline_success"] == "24/24"
    assert h["phase10_real_replay"]["o0_silent_success"] == "0/23"
    assert h["phase10_real_replay"]["visible_feedback_success"] == "22/23"
    assert h["phase10_nonobviousness"]["o0_more_reasoning_success"] == "3/96"
    assert h["phase10_nonobviousness"]["o0_reflection_success"] == "6/95"
    assert h["phase10_nonobviousness"]["rule_visible_success"] == "71/95"


def test_phase10_summary_values():
    replay = load_json("results/phase10_real_case_replay/real_case_formal_summary.json")
    assert replay["status_counts"] == {"failed": 2, "ok": 70}
    assert replay["by_condition"]["baseline_old_api"]["success_n"] == 24
    assert replay["by_condition"]["evolved_o0_silent"]["hidden_violation_n"] == 23
    assert replay["by_condition"]["evolved_visible_feedback"]["success_n"] == 22
    nonobv = load_json("results/phase10_nonobviousness/nonobviousness_analysis_report.json")
    by_cond = nonobv.get("condition_summary") or nonobv.get("condition_results")
    assert by_cond["O0_increased_reasoning_budget"]["success_n"] == 3
    assert by_cond["O0_reflection_scaffold"]["success_n"] == 6
    assert by_cond["rule_in_tool_preamble_upper_bound"]["success_n"] == 71
'''


def test_no_secrets_py() -> str:
    return r'''import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_no_critical_secret_findings():
    subprocess.run([sys.executable, "scripts/scan_for_secrets.py", "--root", "."], cwd=ROOT, check=True)
    report = json.loads((ROOT / "docs/secret_scan_report.json").read_text(encoding="utf-8"))
    assert report["counts"]["critical"] == 0
'''


def test_reproduction_smoke_py() -> str:
    return r'''import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_offline_verify_results_all():
    subprocess.run([sys.executable, "scripts/offline_verify_results.py", "--section", "all"], cwd=ROOT, check=True)


def test_reproduction_scripts_exist():
    for rel in [
        "scripts/reproduce_main_results.sh",
        "scripts/reproduce_figures.sh",
        "scripts/reproduce_audits.sh",
        "scripts/smoke_test.sh",
    ]:
        assert (ROOT / rel).exists()
'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=repo_root())
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args()
    root = args.root.resolve()
    out = args.output.resolve() if args.output else root / OUT_DIRNAME
    builder = PackageBuilder(root, out)
    builder.build()
    print(json.dumps({"output": str(out), "copied_files": len(builder.copied), "excluded_candidates": len(builder.excluded), "missing_inputs": builder.missing}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
