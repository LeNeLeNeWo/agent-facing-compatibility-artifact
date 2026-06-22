# Phase 10D Non-Obviousness Analysis Report

## 1. Executive Summary

- Formal cells analyzed: 288 terminal status rows.
- Status counts: failed=1, ok=286, timeout=1
- Headline result: silent extra reasoning and silent reflection remain low-recovery, while the rule-visible upper bound recovers substantially more often.
- Supports non-obviousness critique response: True.

## 2. Condition-Level Results

| condition | N ok | success | hidden violation | non-ok | avg steps |
| --- | ---: | ---: | ---: | ---: | ---: |
| O0 + more reasoning | 96 | 3/96 (3.1%) | 92/96 (95.8%) | 0 | 17.6 |
| O0 + reflection | 95 | 6/95 (6.3%) | 88/95 (92.6%) | 1 | 17.0 |
| Rule-visible upper bound | 95 | 71/95 (74.7%) | 0/95 (0.0%) | 1 | 21.0 |

Reference rows:

- O0 standard reference: matched=96, ok=96, success=0/96 (0.0%), hidden=96/96 (100.0%), fully matched=True.
- O1 generic error reference: matched=30, ok=27, success=20/27 (74.1%), hidden=0/27 (0.0%), fully matched=False.

## 3. Statistical Analysis

Bootstrap success-rate CIs:
- O0 + more reasoning: 3.1% CI [0.0%, 7.3%]
- O0 + reflection: 6.3% CI [2.1%, 11.6%]
- Rule-visible upper bound: 74.7% CI [66.3%, 83.2%]

Bootstrap differences:
- rule_visible_minus_o0_reasoning: 71.6% CI [62.1%, 81.1%]
- rule_visible_minus_o0_reflection: 68.4% CI [57.9%, 77.9%]
- o0_reflection_minus_o0_reasoning: 3.2% CI [-3.1%, 9.5%]

Cluster bootstrap by source reference cell:
- rule_visible_minus_o0_reasoning: 71.6% CI [62.2%, 80.2%], clusters=96
- rule_visible_minus_o0_reflection: 68.4% CI [58.9%, 77.7%], clusters=96
- o0_reflection_minus_o0_reasoning: 3.2% CI [-2.1%, 8.6%], clusters=96

Fisher exact / chi-square tests:
- rule_visible_minus_o0_reasoning: Fisher p=2.09e-27, chi-square p=3.07e-24, table=[[71, 24], [3, 93]]
- rule_visible_minus_o0_reflection: Fisher p=1.16e-23, chi-square p=7.6e-22, table=[[71, 24], [6, 89]]
- o0_reflection_minus_o0_reasoning: Fisher p=0.331, chi-square p=0.298, table=[[6, 89], [3, 93]]

Sensitivity analysis: provider_error/timeout/failed rows are not counted as agent failures. Primary rates use ok rows only; as-planned denominator rates are provided in the JSON report.

## 4. By Domain / Model / C-Class

Breakdowns are in `nonobviousness_analysis_report.json` under `by_domain`, `by_model`, and `by_semantic_class`. Some cells are small after splitting, so these are diagnostic rather than primary inferential results.

## 5. Integrity Audit

- Rule leakage detected: False.
- Provider errors: 0.
- Fake rows: 0.
- Baseline-success false rows: 0.
- Artifact isolation: Phase 10D did not run agents and did not modify Phase 5/8 raw artifacts or paper body files.

## 6. Paper-Ready Assets

- Table: `IEEE_Conference_Template\tables\nonobviousness_control_auto.tex`
- Figure: `IEEE_Conference_Template\figures\nonobviousness_control.pdf`
- Text snippet: `runs\schema_mutation\phase10\phase10d_nonobviousness_analysis\paper_text_snippet.md`

## 7. Recommendation

Integrate into the paper as a small supplemental control, with an explicit note that the one failed reflection cell and one rule-visible timeout are excluded from ok-row rates and are not counted as agent failures. No retry is required for the central contrast, though retrying the two infrastructure rows would make denominators tidier. The result is strong enough to address the obviousness critique, but it should be presented as a control rather than as a new main finding.

## 8. What Not To Claim

- Do not claim production frequency.
- Do not claim human-validated oracle precision.
- Do not claim all prompting fails.
- Do not claim external validity beyond tested models/tasks.
- Do not claim this replaces semantic observability.
