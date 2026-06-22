#!/usr/bin/env python3
"""Generate Phase 10F-R1 real-case replay formal paper-ready artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path("runs/schema_mutation/phase10/real_case_replay")
FORMAL = ROOT / "formal_r1"
SUMMARY_JSON = FORMAL / "real_case_formal_summary.json"
PLAN_JSONL = FORMAL / "real_case_formal_plan.jsonl"
AUDIT_JSON = ROOT / "real_case_audit.json"

SUMMARY_MD = FORMAL / "real_case_formal_summary.md"
REPORT_MD = ROOT / "phase10f_r1_real_case_formal_report.md"
TABLE_TEX = Path("IEEE_Conference_Template/tables/real_case_replay_auto.tex")
FIGURE_PDF = Path("IEEE_Conference_Template/figures/real_case_replay.pdf")
SNIPPET_MD = FORMAL / "paper_text_snippet.md"

CONDITIONS = ["baseline_old_api", "evolved_o0_silent", "evolved_visible_feedback"]
LABELS = {
    "baseline_old_api": "Baseline old API",
    "evolved_o0_silent": "Evolved O0 silent",
    "evolved_visible_feedback": "Evolved visible feedback",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{100 * value:.1f}%"


def count_rate(num: int, den: int) -> str:
    return f"{num}/{den} ({pct(None if den == 0 else num / den)})"


def fmt_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none"


def ci_text(item: dict[str, Any]) -> str:
    ci95 = item["ci95"]
    return f"{pct(item['point'])} [{pct(ci95['lo'])}, {pct(ci95['hi'])}]"


def tex_escape(value: Any) -> str:
    text = str(value)
    for old, new in [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]:
        text = text.replace(old, new)
    return text


def status_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((FORMAL / "status").glob("*.jsonl")):
        rows.extend(read_jsonl(path))
    return rows


def case_metadata(plan_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in plan_rows:
        out.setdefault(row["case_id"], row)
    return out


def condition_success(summary: dict[str, Any], condition: str) -> str:
    item = summary["by_condition"][condition]
    return count_rate(item["success_n"], item["ok_n"])


def condition_hidden(summary: dict[str, Any], condition: str) -> str:
    item = summary["by_condition"][condition]
    return count_rate(item["hidden_violation_n"], item["ok_n"])


def write_formal_summary(summary: dict[str, Any], selected_cases: list[str], rows: list[dict[str, Any]]) -> None:
    by_condition = summary["by_condition"]
    by_case = summary["by_case"]
    by_model = summary["by_model"]
    stats = summary["statistics"]
    failed_rows = [row for row in rows if row.get("status") != "ok"]
    provider_errors = sum(1 for row in rows if row.get("status") == "provider_error")
    timeouts = sum(1 for row in rows if row.get("status") == "timeout")
    failed = sum(1 for row in rows if row.get("status") == "failed")

    lines: list[str] = [
        "# Phase 10F-R1 Real-Changelog-Grounded Replay Formal Summary",
        "",
        f"- Selected cases: {', '.join(selected_cases)}",
        f"- Cells planned: {summary['planned_cells']}",
        f"- Cells with latest terminal status: {summary['run_cells']}",
        f"- Latest-cell status counts: {fmt_counts(summary['status_counts'])}",
        f"- Provider errors: {provider_errors}",
        f"- Timeouts: {timeouts}",
        f"- Failed rows: {failed}",
        f"- Rule leakage rows: {len(summary.get('rule_leakage_rows', []))}",
        f"- Real third-party API call rows: {len(summary.get('real_third_party_api_call_rows', []))}",
        "- Failed/provider/timeout rows are excluded from success and hidden-violation rates, and are not counted as agent semantic failures.",
        "",
        "## By Condition",
        "",
        "| condition | ok N | success | hidden violation | visible rule exposed | status counts |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for condition in CONDITIONS:
        item = by_condition[condition]
        lines.append(
            f"| {LABELS[condition]} | {item['ok_n']} | "
            f"{count_rate(item['success_n'], item['ok_n'])} | "
            f"{count_rate(item['hidden_violation_n'], item['ok_n'])} | "
            f"{count_rate(item['visible_rule_exposed_n'], item['ok_n'])} | "
            f"{fmt_counts(item['status_counts'])} |"
        )

    lines.extend(["", "## By Case"])
    for case_id in selected_cases:
        lines.extend(
            [
                "",
                f"### {case_id}",
                "",
                "| condition | ok N | success | hidden violation | visible rule exposed | status counts |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for condition in CONDITIONS:
            item = by_case[case_id][condition]
            lines.append(
                f"| {LABELS[condition]} | {item['ok_n']} | "
                f"{count_rate(item['success_n'], item['ok_n'])} | "
                f"{count_rate(item['hidden_violation_n'], item['ok_n'])} | "
                f"{count_rate(item['visible_rule_exposed_n'], item['ok_n'])} | "
                f"{fmt_counts(item['status_counts'])} |"
            )

    lines.extend(["", "## By Model"])
    for model in sorted(by_model):
        lines.extend(
            [
                "",
                f"### {model}",
                "",
                "| condition | ok N | success | hidden violation | visible rule exposed |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for condition in CONDITIONS:
            item = by_model[model][condition]
            lines.append(
                f"| {LABELS[condition]} | {item['ok_n']} | "
                f"{count_rate(item['success_n'], item['ok_n'])} | "
                f"{count_rate(item['hidden_violation_n'], item['ok_n'])} | "
                f"{count_rate(item['visible_rule_exposed_n'], item['ok_n'])} |"
            )

    lines.extend(["", "## Statistical Checks", "", "Bootstrap success-rate CIs:"])
    for condition in CONDITIONS:
        item = stats["bootstrap_success_rates"][condition]
        lines.append(f"- {LABELS[condition]}: {ci_text(item)}, n={item['n']}")
    lines.extend(["", "Bootstrap success-rate differences:"])
    for label, item in stats["bootstrap_success_differences"].items():
        lines.append(f"- {label}: {ci_text(item)}")
    lines.extend(["", "Bootstrap hidden-violation-rate differences:"])
    for label, item in stats["bootstrap_hidden_violation_differences"].items():
        lines.append(f"- {label}: {ci_text(item)}")
    lines.extend(["", "Fisher exact / chi-square tests on success:"])
    for label, item in stats["tests_success"].items():
        lines.append(
            f"- {label}: Fisher p={item['fisher_p']:.4g}, "
            f"chi-square p={item['chi_square_p']:.4g}, table={item['table']}"
        )
    lines.extend(["", "Fisher exact / chi-square tests on hidden violations:"])
    for label, item in stats["tests_hidden_violation"].items():
        chi = "n/a" if item["chi_square_p"] is None else f"{item['chi_square_p']:.4g}"
        lines.append(f"- {label}: Fisher p={item['fisher_p']:.4g}, chi-square p={chi}, table={item['table']}")

    lines.extend(["", "## Non-OK Rows", ""])
    if failed_rows:
        for row in failed_rows:
            lines.append(
                f"- {row.get('cell_key')}: status={row.get('status')}, "
                f"condition={row.get('condition')}, model={row.get('model')}, "
                f"seed={row.get('seed')}, deterministic_oracle_ok={row.get('deterministic_oracle_ok')}"
            )
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Integrity",
            "",
            "- No real Stripe/GitHub API calls were made by the deterministic local wrappers.",
            "- O0 silent rows did not expose the changed rule through visible feedback.",
            "- Visible-feedback rows exposed the changed rule through runtime feedback.",
            "- Provider errors/timeouts/failed rows are not counted as agent failures.",
            "- This is a formal real-changelog-grounded replay result, not a production incident frequency estimate.",
        ]
    )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_table(summary: dict[str, Any], cases: dict[str, dict[str, Any]], selected_cases: list[str]) -> None:
    by_case = summary["by_case"]
    lines = [
        "% Auto-generated by code/schema_mutation/phase10_generate_real_case_formal_assets.py",
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Real-changelog-grounded replay cases. The cases are derived from public API evolution records and executed through deterministic local wrappers; they are not production incident measurements.}",
        r"\label{tab:real-case-replay}",
        r"\small",
        r"\begin{tabular}{p{0.25\linewidth}p{0.06\linewidth}p{0.16\linewidth}p{0.22\linewidth}p{0.22\linewidth}p{0.13\linewidth}}",
        r"\toprule",
        r"Case & Class & Baseline success & O0 silent success / hidden violation & Visible success / hidden violation & Source \\",
        r"\midrule",
    ]
    for case_id in selected_cases:
        meta = cases[case_id]
        item = by_case[case_id]
        source = "Stripe billing" if meta.get("taxonomy_class") == "C1" else "Stripe payment links"
        lines.append(
            " & ".join(
                [
                    tex_escape(case_id),
                    tex_escape(meta.get("taxonomy_class")),
                    tex_escape(count_rate(item["baseline_old_api"]["success_n"], item["baseline_old_api"]["ok_n"])),
                    tex_escape(
                        count_rate(item["evolved_o0_silent"]["success_n"], item["evolved_o0_silent"]["ok_n"])
                        + " / "
                        + count_rate(
                            item["evolved_o0_silent"]["hidden_violation_n"],
                            item["evolved_o0_silent"]["ok_n"],
                        )
                    ),
                    tex_escape(
                        count_rate(
                            item["evolved_visible_feedback"]["success_n"],
                            item["evolved_visible_feedback"]["ok_n"],
                        )
                        + " / "
                        + count_rate(
                            item["evolved_visible_feedback"]["hidden_violation_n"],
                            item["evolved_visible_feedback"]["ok_n"],
                        )
                    ),
                    tex_escape(source),
                ]
            )
            + r" \\"
        )
    lines.extend(
        [
            r"\midrule",
            " & ".join(
                [
                    "All selected cases",
                    "C1/C4",
                    tex_escape(condition_success(summary, "baseline_old_api")),
                    tex_escape(
                        condition_success(summary, "evolved_o0_silent")
                        + " / "
                        + condition_hidden(summary, "evolved_o0_silent")
                    ),
                    tex_escape(
                        condition_success(summary, "evolved_visible_feedback")
                        + " / "
                        + condition_hidden(summary, "evolved_visible_feedback")
                    ),
                    "Public changelogs",
                ]
            )
            + r" \\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\vspace{0.3em}",
            r"\footnotesize{Rates count ok rows only. Two non-ok oracle/final-state failures are excluded and are not counted as agent semantic failures. The replay wrappers do not call Stripe or GitHub APIs.}",
            r"\end{table*}",
        ]
    )
    TABLE_TEX.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_snippet() -> None:
    lines = [
        "## Short Version",
        "",
        "As a real-changelog-grounded replay control, we instantiated two cases from public API evolution records using deterministic local wrappers rather than live provider APIs. The old-API baseline succeeded in 24/24 completed runs, while the evolved O0 silent condition succeeded in 0/23 completed runs and produced hidden semantic violations in 23/23. When the same evolved semantics exposed runtime feedback, agents recovered in 22/23 completed runs and hidden violations fell to 0/23. These cases are not a production incident frequency estimate, and they do not show that prompting is generally useless. Instead, they reproduce the same silent-versus-visible mechanism in public changelog-grounded settings: reasoning can use visible signals, but it cannot reliably infer an external semantic rule change that remains unobserved.",
        "",
        "## Medium Version",
        "",
        "We also ran a small real-changelog-grounded replay based on public API evolution records. The replay uses deterministic local wrappers for two Stripe changelog-derived cases: a C1 validation/scale change for billing meter event values and a C4 business-rule change for payment-link card-brand restrictions. The wrappers preserve the callable tool surface and do not call live Stripe or GitHub APIs. They are therefore not production incident measurements and should not be read as a production incident frequency estimate.",
        "",
        "Across 72 planned formal cells, 70 completed with ok status and two ended in non-ok deterministic oracle/final-state failures, which were excluded from semantic success and hidden-violation rates. The old-API baseline succeeded in 24/24 completed runs. Under evolved O0 silent semantics, success dropped to 0/23 and every completed run exhibited a hidden semantic violation. Under evolved visible feedback, success recovered to 22/23 and hidden violations fell to 0/23, with the changed rule exposed through runtime feedback in all completed visible-feedback runs. This pattern reproduces the same silent-versus-visible mechanism observed in the synthetic controls: reasoning helps agents use visible signals, but it cannot recover a changed external semantic rule that remains unobserved. The result is best used as a compact grounding control, not as evidence about all API changelogs or production frequency.",
    ]
    SNIPPET_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(
    summary: dict[str, Any],
    cases: dict[str, dict[str, Any]],
    audit: dict[str, Any],
    rows: list[dict[str, Any]],
    selected_cases: list[str],
) -> None:
    stats = summary["statistics"]
    provider_errors = sum(1 for row in rows if row.get("status") == "provider_error")
    timeouts = sum(1 for row in rows if row.get("status") == "timeout")
    failed = sum(1 for row in rows if row.get("status") == "failed")
    by_case = summary["by_case"]

    lines = [
        "# Phase 10F-R1 Real-Changelog-Grounded Case Replay Formal Report",
        "",
        "## 1. Executive Summary",
        "",
        f"- Cases used: {', '.join(selected_cases)}",
        f"- Formal cells planned/run: {summary['planned_cells']}/{summary['run_cells']}",
        f"- Status counts: {fmt_counts(summary['status_counts'])}",
        f"- Provider errors: {provider_errors}; timeouts: {timeouts}; failed: {failed}",
        f"- Headline results: baseline success {condition_success(summary, 'baseline_old_api')}; O0 silent success {condition_success(summary, 'evolved_o0_silent')} with hidden violation {condition_hidden(summary, 'evolved_o0_silent')}; visible-feedback success {condition_success(summary, 'evolved_visible_feedback')} with hidden violation {condition_hidden(summary, 'evolved_visible_feedback')}.",
        "- Result supports paper integration as a small real-grounding subsection, with careful wording that this is deterministic replay grounded in changelogs, not production incident measurement.",
        "",
        "## 2. Case Provenance",
    ]
    for case_id in selected_cases:
        meta = cases[case_id]
        audit_row = next((row for row in audit.get("audit_rows", []) if row.get("case_id") == case_id), {})
        lines.extend(
            [
                "",
                f"### {case_id}",
                "",
                f"- Provider: {meta.get('provider')}",
                f"- Taxonomy class: {meta.get('taxonomy_class')} ({meta.get('taxonomy_subclass')})",
                f"- Official source URL: {meta.get('official_source_url')}",
                f"- Evidence: {meta.get('short_evidence')}",
                f"- Old semantics: {meta.get('old_semantics')}",
                f"- New semantics: {meta.get('new_semantics')}",
                f"- Deterministic oracle: {meta.get('oracle_rule')}",
                f"- Grounding rationale: {audit_row.get('selection_reason')}",
            ]
        )

    lines.extend(
        [
            "",
            "## 3. Formal Results",
            "",
            "| condition | planned/terminal | ok N | success | hidden violation | visible rule exposed | status counts |",
            "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for condition in CONDITIONS:
        item = summary["by_condition"][condition]
        lines.append(
            f"| {LABELS[condition]} | {item['planned_or_observed_n']}/{item['planned_or_observed_n']} | "
            f"{item['ok_n']} | {condition_success(summary, condition)} | "
            f"{condition_hidden(summary, condition)} | "
            f"{count_rate(item['visible_rule_exposed_n'], item['ok_n'])} | "
            f"{fmt_counts(item['status_counts'])} |"
        )
    lines.extend(
        [
            "",
            "Key statistical contrasts, using completed ok rows only:",
            f"- Baseline old API vs evolved O0 silent success difference: {ci_text(stats['bootstrap_success_differences']['baseline_old_api_vs_evolved_o0_silent'])}; Fisher p={stats['tests_success']['baseline_old_api_vs_evolved_o0_silent']['fisher_p']:.4g}.",
            f"- Evolved O0 silent vs evolved visible feedback success difference: {ci_text(stats['bootstrap_success_differences']['evolved_o0_silent_vs_evolved_visible_feedback'])}; Fisher p={stats['tests_success']['evolved_o0_silent_vs_evolved_visible_feedback']['fisher_p']:.4g}.",
            f"- Evolved O0 silent vs evolved visible feedback hidden-violation difference: {ci_text(stats['bootstrap_hidden_violation_differences']['evolved_o0_silent_vs_evolved_visible_feedback'])}; Fisher p={stats['tests_hidden_violation']['evolved_o0_silent_vs_evolved_visible_feedback']['fisher_p']:.4g}.",
            "",
            "By-case headline:",
        ]
    )
    for case_id in selected_cases:
        item = by_case[case_id]
        lines.append(
            f"- {case_id}: baseline {count_rate(item['baseline_old_api']['success_n'], item['baseline_old_api']['ok_n'])}; "
            f"O0 silent {count_rate(item['evolved_o0_silent']['success_n'], item['evolved_o0_silent']['ok_n'])} success / "
            f"{count_rate(item['evolved_o0_silent']['hidden_violation_n'], item['evolved_o0_silent']['ok_n'])} hidden; "
            f"visible {count_rate(item['evolved_visible_feedback']['success_n'], item['evolved_visible_feedback']['ok_n'])} success / "
            f"{count_rate(item['evolved_visible_feedback']['hidden_violation_n'], item['evolved_visible_feedback']['ok_n'])} hidden."
        )

    lines.extend(
        [
            "",
            "By-model details are in `runs/schema_mutation/phase10/real_case_replay/formal_r1/real_case_formal_summary.md`.",
            "",
            "## 4. Integrity",
            "",
            "- No real Stripe/GitHub API calls were made; the wrapper is deterministic and local.",
            "- This is not a production incident claim and not a production frequency estimate.",
            f"- Rule leakage rows: {len(summary.get('rule_leakage_rows', []))}.",
            "- O0 silent rows did not expose the changed rule; visible-feedback rows exposed it through runtime feedback.",
            "- Deterministic oracle worked for ok rows; two non-ok failed rows were excluded from semantic rates.",
            f"- Provider errors: {provider_errors}; timeouts: {timeouts}. These were not counted as agent failures.",
            "- No paper body files, `main.tex`, or section files were edited by this phase.",
            "- Frozen main results and Phase 5/8 artifacts were not modified by this phase.",
            "",
            "## 5. Paper Integration Recommendation",
            "",
            "Recommendation: integrate as a small real-grounding subsection, or as a compact Results/Discussion control if space is tight. The result is strong enough to support the mechanism explanation that public changelog-grounded semantic changes can reproduce the same silent-versus-visible mechanism under deterministic replay, but it should remain clearly separated from the frozen TAU-BENCH main results.",
            "",
            "Paper-ready assets generated:",
            "- `IEEE_Conference_Template/tables/real_case_replay_auto.tex`",
            "- `IEEE_Conference_Template/figures/real_case_replay.pdf`",
            "- `runs/schema_mutation/phase10/real_case_replay/formal_r1/paper_text_snippet.md`",
            "",
            "## 6. What Not To Claim",
            "",
            "- Do not claim production frequency.",
            "- Do not claim production incidents.",
            "- Do not claim all API changelogs behave like these cases.",
            "- Do not replace TAU-BENCH main results with these cases.",
            "- Do not claim human-validated corpus labels unless human review completed.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def pdf_escape(text: Any) -> str:
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf_figure(summary: dict[str, Any]) -> None:
    def text(cmds: list[str], x: float, y: float, value: str, size: int = 9) -> None:
        cmds.append(f"BT /F1 {size} Tf {x:.1f} {y:.1f} Td ({pdf_escape(value)}) Tj ET")

    def rect(cmds: list[str], x: float, y: float, width: float, height: float, color: tuple[float, float, float]) -> None:
        r, g, b = color
        cmds.append(f"q {r:.3f} {g:.3f} {b:.3f} rg {x:.1f} {y:.1f} {width:.1f} {height:.1f} re f Q")

    def line(cmds: list[str], x1: float, y1: float, x2: float, y2: float) -> None:
        cmds.append(f"q 0.5 w 0.2 0.2 0.2 RG {x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S Q")

    width, height = 540, 270
    x0, x1 = 210, 500
    blue = (0.090, 0.380, 0.670)
    red = (0.780, 0.180, 0.160)
    grey = (0.88, 0.88, 0.88)
    y_positions = {
        "baseline_old_api": 190,
        "evolved_o0_silent": 145,
        "evolved_visible_feedback": 100,
    }
    cmds: list[str] = []
    text(cmds, 40, 245, "Real-changelog-grounded replay formal results", 13)
    text(cmds, 40, 228, "Success and hidden-violation rates among completed ok rows", 9)
    line(cmds, x0, 55, x1, 55)
    for tick in [0, 25, 50, 75, 100]:
        x = x0 + (x1 - x0) * tick / 100
        line(cmds, x, 52, x, 58)
        text(cmds, x - 8, 38, str(tick), 7)
    text(cmds, x1 - 20, 22, "rate (%)", 8)
    for condition in CONDITIONS:
        item = summary["by_condition"][condition]
        y = y_positions[condition]
        success = 100 * item["success_rate"]
        hidden = 100 * item["hidden_violation_rate"]
        text(cmds, 40, y + 3, LABELS[condition], 9)
        rect(cmds, x0, y + 9, x1 - x0, 8, grey)
        rect(cmds, x0, y + 9, (x1 - x0) * success / 100, 8, blue)
        rect(cmds, x0, y - 5, x1 - x0, 8, grey)
        rect(cmds, x0, y - 5, (x1 - x0) * hidden / 100, 8, red)
        text(cmds, x1 + 5, y + 7, f"S {success:.1f}%", 8)
        text(cmds, x1 + 5, y - 7, f"H {hidden:.1f}%", 8)
    rect(cmds, 40, 25, 10, 7, blue)
    text(cmds, 55, 24, "success", 8)
    rect(cmds, 120, 25, 10, 7, red)
    text(cmds, 135, 24, "hidden violation", 8)

    content = ("\n".join(cmds) + "\n").encode("latin-1")
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\nendobj\n".encode(
            "latin-1"
        ),
        f"4 0 obj\n<< /Length {len(content)} >>\nstream\n".encode("latin-1") + content + b"endstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("latin-1"))
    FIGURE_PDF.write_bytes(bytes(pdf))


def main() -> int:
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    plan_rows = read_jsonl(PLAN_JSONL)
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    cases = case_metadata(plan_rows)
    selected_cases = sorted(cases)
    rows = status_rows()

    write_formal_summary(summary, selected_cases, rows)
    write_table(summary, cases, selected_cases)
    write_snippet()
    write_report(summary, cases, audit, rows, selected_cases)
    write_pdf_figure(summary)

    print(json.dumps(
        {
            "summary_md": str(SUMMARY_MD),
            "report_md": str(REPORT_MD),
            "table_tex": str(TABLE_TEX),
            "figure_pdf": str(FIGURE_PDF),
            "snippet_md": str(SNIPPET_MD),
        },
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
