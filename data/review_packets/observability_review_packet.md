# Phase 5C Observability Gradient Review Packet

- generated_at: 2026-06-14T12:15:38
- data source: formal `observability_from_baseline_*_status.jsonl` rows only
- success definition: `reward >= 0.5`
- uplift CI: deterministic nonparametric bootstrap over observed rewards, 5,000 rounds

## 1. Integrity Checks

| Check | Value |
| --- | --- |
| expected total | 525 |
| actual formal rows | 525 |
| ok | 525 |
| failed | 0 |
| timeout | 0 |
| provider_error | 0 |
| fake_run count | 0 |
| baseline_success=false count | 0 |
| wyzlab count | 0 |
| mutation_candidate count | 0 |
| smoke rows included? | no |
| missing critical fields count | 0 |
| O0_silent count | 105 |
| O1_generic_error count | 105 |
| O2_policy_error count | 105 |
| O3_structured_policy_error count | 105 |
| O4_migration_note count | 105 |

Critical field missing counts:
| Field | Missing |
| --- | --- |
| observability_level | 0 |
| env | 0 |
| model | 0 |
| provider | 0 |
| task_id | 0 |
| seed | 0 |
| reward | 0 |
| baseline_success | 0 |
| visible_policy_error | 0 |
| hidden_business_rule_violation | 0 |
| structured_policy_error_visible | 0 |
| migration_note_visible | 0 |

## 2. Overall O-Level Success Table

| Level | N | Success | Success rate | Wilson CI | Mean reward | Hidden violation rate | Visible signal rate | Recovery attempted | Recovery success |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| O0_silent | 105 | 43 | 0.410 | [0.320, 0.505] | 0.410 | 0.533 | 0.000 | 0 (0.000) | 0 (0.000) |
| O1_generic_error | 105 | 90 | 0.857 | [0.778, 0.911] | 0.857 | 0.000 | 0.543 | 10 (0.095) | 7 (0.067) |
| O2_policy_error | 105 | 85 | 0.810 | [0.724, 0.873] | 0.810 | 0.000 | 0.543 | 10 (0.095) | 7 (0.067) |
| O3_structured_policy_error | 105 | 89 | 0.848 | [0.767, 0.904] | 0.848 | 0.000 | 0.533 | 10 (0.095) | 6 (0.057) |
| O4_migration_note | 105 | 90 | 0.857 | [0.778, 0.911] | 0.857 | 0.000 | 1.000 | 7 (0.067) | 4 (0.038) |

## 3. Per Model O-Level Table

| Env | Model | Provider | Level | N | Success | Rate | Mean reward | Hidden viol. | Visible signal | Recovery success |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| retail | dashscope/glm-5.1 | dashscope | O0_silent | 32 | 13 | 0.406 | 0.406 | 0.562 | 0.000 | 0.000 |
| retail | dashscope/glm-5.1 | dashscope | O1_generic_error | 32 | 25 | 0.781 | 0.781 | 0.000 | 0.594 | 0.094 |
| retail | dashscope/glm-5.1 | dashscope | O2_policy_error | 32 | 28 | 0.875 | 0.875 | 0.000 | 0.625 | 0.125 |
| retail | dashscope/glm-5.1 | dashscope | O3_structured_policy_error | 32 | 28 | 0.875 | 0.875 | 0.000 | 0.625 | 0.094 |
| retail | dashscope/glm-5.1 | dashscope | O4_migration_note | 32 | 27 | 0.844 | 0.844 | 0.000 | 1.000 | 0.000 |
| retail | dashscope/kimi-k2.6 | dashscope | O0_silent | 26 | 13 | 0.500 | 0.500 | 0.500 | 0.000 | 0.000 |
| retail | dashscope/kimi-k2.6 | dashscope | O1_generic_error | 26 | 22 | 0.846 | 0.846 | 0.000 | 0.500 | 0.038 |
| retail | dashscope/kimi-k2.6 | dashscope | O2_policy_error | 26 | 21 | 0.808 | 0.808 | 0.000 | 0.500 | 0.038 |
| retail | dashscope/kimi-k2.6 | dashscope | O3_structured_policy_error | 26 | 22 | 0.846 | 0.846 | 0.000 | 0.500 | 0.038 |
| retail | dashscope/kimi-k2.6 | dashscope | O4_migration_note | 26 | 22 | 0.846 | 0.846 | 0.000 | 1.000 | 0.038 |
| retail | dashscope/qwen-max | dashscope | O0_silent | 24 | 4 | 0.167 | 0.167 | 0.625 | 0.000 | 0.000 |
| retail | dashscope/qwen-max | dashscope | O1_generic_error | 24 | 21 | 0.875 | 0.875 | 0.000 | 0.583 | 0.083 |
| retail | dashscope/qwen-max | dashscope | O2_policy_error | 24 | 16 | 0.667 | 0.667 | 0.000 | 0.583 | 0.083 |
| retail | dashscope/qwen-max | dashscope | O3_structured_policy_error | 24 | 18 | 0.750 | 0.750 | 0.000 | 0.542 | 0.083 |
| retail | dashscope/qwen-max | dashscope | O4_migration_note | 24 | 20 | 0.833 | 0.833 | 0.000 | 1.000 | 0.125 |
| retail | deepseek/deepseek-v4-flash | deepseek | O0_silent | 23 | 13 | 0.565 | 0.565 | 0.435 | 0.000 | 0.000 |
| retail | deepseek/deepseek-v4-flash | deepseek | O1_generic_error | 23 | 22 | 0.957 | 0.957 | 0.000 | 0.478 | 0.043 |
| retail | deepseek/deepseek-v4-flash | deepseek | O2_policy_error | 23 | 20 | 0.870 | 0.870 | 0.000 | 0.435 | 0.000 |
| retail | deepseek/deepseek-v4-flash | deepseek | O3_structured_policy_error | 23 | 21 | 0.913 | 0.913 | 0.000 | 0.435 | 0.000 |
| retail | deepseek/deepseek-v4-flash | deepseek | O4_migration_note | 23 | 21 | 0.913 | 0.913 | 0.000 | 1.000 | 0.000 |

## 4. Uplift Table

Overall uplift relative to O0:
| Contrast | Point estimate | Bootstrap 95% CI |
| --- | --- | --- |
| O1_generic_error-O0 | 0.448 | [0.333, 0.562] |
| O2_policy_error-O0 | 0.400 | [0.286, 0.524] |
| O3_structured_policy_error-O0 | 0.438 | [0.324, 0.552] |
| O4_migration_note-O0 | 0.448 | [0.333, 0.562] |

| Env | Model | O1-O0 | O2-O0 | O3-O0 | O4-O0 |
| --- | --- | --- | --- | --- | --- |
| retail | dashscope/glm-5.1 | 0.375 [0.156, 0.594] | 0.469 [0.250, 0.656] | 0.469 [0.250, 0.656] | 0.438 [0.219, 0.656] |
| retail | dashscope/kimi-k2.6 | 0.346 [0.115, 0.577] | 0.308 [0.077, 0.538] | 0.346 [0.115, 0.577] | 0.346 [0.115, 0.577] |
| retail | dashscope/qwen-max | 0.708 [0.500, 0.875] | 0.500 [0.250, 0.750] | 0.583 [0.333, 0.792] | 0.667 [0.458, 0.875] |
| retail | deepseek/deepseek-v4-flash | 0.391 [0.174, 0.609] | 0.304 [0.043, 0.565] | 0.348 [0.130, 0.565] | 0.348 [0.130, 0.565] |

## 5. Monotonicity / Mechanism Check

| Env | Model | Provider | Non-decreasing? | Violations | Rates |
| --- | --- | --- | --- | --- | --- |
| retail | dashscope/glm-5.1 | dashscope | no | O4_migration_note < O3_structured_policy_error | O0_silent=0.406, O1_generic_error=0.781, O2_policy_error=0.875, O3_structured_policy_error=0.875, O4_migration_note=0.844 |
| retail | dashscope/kimi-k2.6 | dashscope | no | O2_policy_error < O1_generic_error | O0_silent=0.500, O1_generic_error=0.846, O2_policy_error=0.808, O3_structured_policy_error=0.846, O4_migration_note=0.846 |
| retail | dashscope/qwen-max | dashscope | no | O2_policy_error < O1_generic_error | O0_silent=0.167, O1_generic_error=0.875, O2_policy_error=0.667, O3_structured_policy_error=0.750, O4_migration_note=0.833 |
| retail | deepseek/deepseek-v4-flash | deepseek | no | O2_policy_error < O1_generic_error | O0_silent=0.565, O1_generic_error=0.957, O2_policy_error=0.870, O3_structured_policy_error=0.913, O4_migration_note=0.913 |

## 6. Expected Semantic Flags

| Level | N | visible_policy_error | generic_error_visible | structured_policy_error_visible | migration_note_visible | hidden_business_rule_violation | visible_signal |
| --- | --- | --- | --- | --- | --- | --- | --- |
| O0_silent | 105 | 0.000 | 0.000 | 0.000 | 0.000 | 0.533 | 0.000 |
| O1_generic_error | 105 | 0.543 | 0.543 | 0.000 | 0.000 | 0.000 | 0.543 |
| O2_policy_error | 105 | 0.543 | 0.000 | 0.000 | 0.000 | 0.000 | 0.543 |
| O3_structured_policy_error | 105 | 0.533 | 0.000 | 0.533 | 0.000 | 0.000 | 0.533 |
| O4_migration_note | 105 | 0.514 | 0.000 | 0.514 | 1.000 | 0.000 | 1.000 |

## 7. Recommended Paper Interpretation

- case: B
- draft: The results support a weaker but still useful claim: structured diagnostics and migration notes improve recoverability over silent drift, while generic or coarse errors are less reliable.

## 8. LaTeX Table And Figure Checks

| Path | Exists | Non-empty | Size bytes | Modified time |
| --- | --- | --- | --- | --- |
| IEEE_Conference_Template\tables\observability_gradient_auto.tex | yes | yes | 1675 | 2026-06-14T11:35:08 |
| IEEE_Conference_Template\figures\observability_gradient_curve.pdf | yes | yes | 16715 | 2026-06-14T11:35:12 |
| IEEE_Conference_Template\figures\observability_uplift_forest.pdf | yes | yes | 14223 | 2026-06-14T11:35:13 |

## 9. Smoke Contamination Check

| Check | Value |
| --- | --- |
| summary raw rows | 846 |
| summary latest rows | 825 |
| fake rows excluded | 4 |
| smoke rows excluded | 21 |
| summary warnings | excluded 4 local_fake smoke rows; excluded 21 smoke rows |
| observability gradient rows | 20 |
| observability gradient paired total | 525 |

