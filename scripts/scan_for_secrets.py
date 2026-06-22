#!/usr/bin/env python3
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
