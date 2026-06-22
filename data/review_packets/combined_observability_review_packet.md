# Combined Observability Review Packet

Scope: Phase 5 formal retail and airline observability gradients; offline aggregation only.

## Integrity
| Check | Value |
| --- | --- |
| retail_formal | 525 |
| airline_formal | 1290 |
| total_formal | 1815 |
| ok | 1815 |
| provider_error | 0 |
| timeout | 0 |
| failed | 0 |
| smoke_included | no |
| retry_duplicate | no |
| fake_run_count | 0 |
| baseline_success_false_count | 0 |
| wyzlab_count | 0 |
| mutation_candidate_count | 0 |

## Domain And Combined Success Rates
| Domain | O0 | O1 | O2 | O3 | O4 | O4--O0 CI |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| retail | 0.410 | 0.857 | 0.810 | 0.848 | 0.857 | 0.448 [0.333, 0.562] |
| airline | 0.539 | 0.837 | 0.860 | 0.853 | 0.845 | 0.306 [0.233, 0.380] |
| combined | 0.501 | 0.843 | 0.846 | 0.851 | 0.848 | 0.347 [0.289, 0.405] |

## Per Domain / Model
| Env | Model | O0 | O1 | O2 | O3 | O4 | O4--O0 | Monotone? |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| airline | dashscope/glm-5.1 | 0.553 | 0.842 | 0.908 | 0.882 | 0.855 | 0.303 | no |
| airline | dashscope/kimi-k2.6 | 0.548 | 0.932 | 0.877 | 0.890 | 0.890 | 0.342 | no |
| airline | dashscope/qwen-max | 0.414 | 0.552 | 0.793 | 0.690 | 0.655 | 0.241 | no |
| airline | deepseek/deepseek-v4-flash | 0.562 | 0.850 | 0.825 | 0.850 | 0.863 | 0.300 | no |
| retail | dashscope/glm-5.1 | 0.406 | 0.781 | 0.875 | 0.875 | 0.844 | 0.438 | no |
| retail | dashscope/kimi-k2.6 | 0.500 | 0.846 | 0.808 | 0.846 | 0.846 | 0.346 | no |
| retail | dashscope/qwen-max | 0.167 | 0.875 | 0.667 | 0.750 | 0.833 | 0.667 | no |
| retail | deepseek/deepseek-v4-flash | 0.565 | 0.957 | 0.870 | 0.913 | 0.913 | 0.348 | no |

## Monotonicity

- airline / dashscope/glm-5.1: non-monotone; O3_structured_policy_error < O2_policy_error, O4_migration_note < O3_structured_policy_error.
- airline / dashscope/kimi-k2.6: non-monotone; O2_policy_error < O1_generic_error.
- airline / dashscope/qwen-max: non-monotone; O3_structured_policy_error < O2_policy_error, O4_migration_note < O3_structured_policy_error.
- airline / deepseek/deepseek-v4-flash: non-monotone; O2_policy_error < O1_generic_error.
- retail / dashscope/glm-5.1: non-monotone; O4_migration_note < O3_structured_policy_error.
- retail / dashscope/kimi-k2.6: non-monotone; O2_policy_error < O1_generic_error.
- retail / dashscope/qwen-max: non-monotone; O2_policy_error < O1_generic_error.
- retail / deepseek/deepseek-v4-flash: non-monotone; O2_policy_error < O1_generic_error.

## Recommended Interpretation

- Observability improves recoverability over silent drift.
- The gradients are not strictly monotonic by feedback specificity.
- Generic errors often already provide a recovery channel.
- Structured diagnostics and migration notes remain robustly better than silent drift.
- Combined aggregation should not hide domain differences; retail and airline are reported separately.
