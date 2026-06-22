# Airline Observability Review Packet

Scope: Phase 5D airline formal observability gradient, non-WYZLab baseline-successful cells only.

## Integrity
| Check | Value |
| --- | --- |
| expected total | 1290 |
| raw status rows in formal files | 1344 |
| deduplicated latest rows | 1290 |
| actual formal rows | 1290 |
| duplicate rows removed by cell_key | 54 |
| ok / provider_error / timeout / failed | 1290 / 0 / 0 / 0 |
| fake_run / baseline_success=false / wyzlab | 0 / 0 / 0 |
| smoke rows included | no |
| missing critical fields | 0 |
| integrity pass | yes |

Level counts: O0_silent=258, O1_generic_error=258, O2_policy_error=258, O3_structured_policy_error=258, O4_migration_note=258.

## Overall O-Level Success
| Level | N | Success | Success rate | Wilson CI | Mean reward | Hidden viol. | Visible signal | Recovery attempted | Recovery success |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| O0_silent | 258 | 139 | 53.9% | [47.8%, 59.9%] | 0.539 | 40.7% | 0.0% | 0 (0.0%) | 0 (0.0%) |
| O1_generic_error | 258 | 216 | 83.7% | [78.7%, 87.7%] | 0.837 | 0.0% | 42.6% | 48 (18.6%) | 26 (10.1%) |
| O2_policy_error | 258 | 222 | 86.0% | [81.3%, 89.7%] | 0.860 | 0.0% | 44.6% | 48 (18.6%) | 26 (10.1%) |
| O3_structured_policy_error | 258 | 220 | 85.3% | [80.4%, 89.1%] | 0.853 | 0.0% | 42.2% | 42 (16.3%) | 21 (8.1%) |
| O4_migration_note | 258 | 218 | 84.5% | [79.6%, 88.4%] | 0.845 | 0.0% | 100.0% | 47 (18.2%) | 28 (10.9%) |

## Per Model O-Level Success
| Env | Model | Provider | Level | N | Success | Rate | Mean reward | Hidden viol. | Visible signal | Recovery success |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| airline | dashscope/glm-5.1 | dashscope | O0_silent | 76 | 42 | 55.3% | 0.553 | 42.1% | 0.0% | 0.0% |
| airline | dashscope/glm-5.1 | dashscope | O1_generic_error | 76 | 64 | 84.2% | 0.842 | 0.0% | 46.1% | 7.9% |
| airline | dashscope/glm-5.1 | dashscope | O2_policy_error | 76 | 69 | 90.8% | 0.908 | 0.0% | 46.1% | 9.2% |
| airline | dashscope/glm-5.1 | dashscope | O3_structured_policy_error | 76 | 67 | 88.2% | 0.882 | 0.0% | 44.7% | 6.6% |
| airline | dashscope/glm-5.1 | dashscope | O4_migration_note | 76 | 65 | 85.5% | 0.855 | 0.0% | 100.0% | 7.9% |
| airline | dashscope/kimi-k2.6 | dashscope | O0_silent | 73 | 40 | 54.8% | 0.548 | 35.6% | 0.0% | 0.0% |
| airline | dashscope/kimi-k2.6 | dashscope | O1_generic_error | 73 | 68 | 93.2% | 0.932 | 0.0% | 37.0% | 12.3% |
| airline | dashscope/kimi-k2.6 | dashscope | O2_policy_error | 73 | 64 | 87.7% | 0.877 | 0.0% | 41.1% | 11.0% |
| airline | dashscope/kimi-k2.6 | dashscope | O3_structured_policy_error | 73 | 65 | 89.0% | 0.890 | 0.0% | 35.6% | 6.8% |
| airline | dashscope/kimi-k2.6 | dashscope | O4_migration_note | 73 | 65 | 89.0% | 0.890 | 0.0% | 100.0% | 9.6% |
| airline | dashscope/qwen-max | dashscope | O0_silent | 29 | 12 | 41.4% | 0.414 | 48.3% | 0.0% | 0.0% |
| airline | dashscope/qwen-max | dashscope | O1_generic_error | 29 | 16 | 55.2% | 0.552 | 0.0% | 55.2% | 13.8% |
| airline | dashscope/qwen-max | dashscope | O2_policy_error | 29 | 23 | 79.3% | 0.793 | 0.0% | 58.6% | 20.7% |
| airline | dashscope/qwen-max | dashscope | O3_structured_policy_error | 29 | 20 | 69.0% | 0.690 | 0.0% | 55.2% | 17.2% |
| airline | dashscope/qwen-max | dashscope | O4_migration_note | 29 | 19 | 65.5% | 0.655 | 0.0% | 100.0% | 24.1% |
| airline | deepseek/deepseek-v4-flash | deepseek | O0_silent | 80 | 45 | 56.2% | 0.562 | 41.2% | 0.0% | 0.0% |
| airline | deepseek/deepseek-v4-flash | deepseek | O1_generic_error | 80 | 68 | 85.0% | 0.850 | 0.0% | 40.0% | 8.8% |
| airline | deepseek/deepseek-v4-flash | deepseek | O2_policy_error | 80 | 66 | 82.5% | 0.825 | 0.0% | 41.2% | 6.2% |
| airline | deepseek/deepseek-v4-flash | deepseek | O3_structured_policy_error | 80 | 68 | 85.0% | 0.850 | 0.0% | 41.2% | 7.5% |
| airline | deepseek/deepseek-v4-flash | deepseek | O4_migration_note | 80 | 69 | 86.2% | 0.863 | 0.0% | 100.0% | 10.0% |

## Uplift vs O0
Overall uplift: O1-O0=29.8%, O2-O0=32.2%, O3-O0=31.4%, O4-O0=30.6%.
Overall O4-O0 bootstrap CI: point=30.6%, 95% CI=[23.3%, 38.0%], iterations=5000.

| Env | Model | Provider | O1-O0 | O2-O0 | O3-O0 | O4-O0 | O4-O0 boot CI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| airline | dashscope/glm-5.1 | dashscope | 28.9% | 35.5% | 32.9% | 30.3% | [15.8%, 43.4%] |
| airline | dashscope/kimi-k2.6 | dashscope | 38.4% | 32.9% | 34.2% | 34.2% | [20.5%, 47.9%] |
| airline | dashscope/qwen-max | dashscope | 13.8% | 37.9% | 27.6% | 24.1% | [0.0%, 48.3%] |
| airline | deepseek/deepseek-v4-flash | deepseek | 28.7% | 26.2% | 28.7% | 30.0% | [16.3%, 43.7%] |

## Monotonicity
| Env | Model | Nondecreasing | Violations | O0/O1/O2/O3/O4 |
| --- | --- | --- | --- | --- |
| airline | dashscope/glm-5.1 | no | O3 < O2, O4 < O3 | 55.3% / 84.2% / 90.8% / 88.2% / 85.5% |
| airline | dashscope/kimi-k2.6 | no | O2 < O1 | 54.8% / 93.2% / 87.7% / 89.0% / 89.0% |
| airline | dashscope/qwen-max | no | O3 < O2, O4 < O3 | 41.4% / 55.2% / 79.3% / 69.0% / 65.5% |
| airline | deepseek/deepseek-v4-flash | no | O2 < O1 | 56.2% / 85.0% / 82.5% / 85.0% / 86.2% |

## Flag Sanity
| Level | N | Oracle viol. N | Visible policy | Generic visible | Structured visible | Migration note | Hidden viol. | Structured | oracle | Migration | oracle |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| O0_silent | 258 | 105 | 0.0% | 0.0% | 0.0% | 0.0% | 40.7% | 0.0% | 0.0% |
| O1_generic_error | 258 | 110 | 42.6% | 42.6% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| O2_policy_error | 258 | 115 | 44.6% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| O3_structured_policy_error | 258 | 109 | 42.2% | 0.0% | 42.2% | 0.0% | 0.0% | 100.0% | 0.0% |
| O4_migration_note | 258 | 115 | 44.6% | 0.0% | 44.6% | 100.0% | 0.0% | 100.0% | 100.0% |

## Interpretation
Case: B_partial_gradient

The results support a weaker but useful claim: structured diagnostics and migration notes improve recoverability over silent drift, while the full airline curve is not strictly monotonic across all models.

Summary checks: smoke rows excluded = yes; retry rows deduplicated by cell_key = yes; WYZLab excluded = yes.
