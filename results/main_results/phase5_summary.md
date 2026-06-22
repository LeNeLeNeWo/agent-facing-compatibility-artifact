# Phase 5 Summary

- inputs: ['<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_baseline_nonwyzlab_0000_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_baseline_nonwyzlab_0001_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_baseline_nonwyzlab_0002_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_baseline_nonwyzlab_0003_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_baseline_nonwyzlab_0004_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_baseline_nonwyzlab_0005_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0000_retry_provider_error_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0000_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0001_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0002_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0003_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0004_retry_provider_error_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0004_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0005_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0006_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0007_retry_provider_error_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0007_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0008_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0009_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0010_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0011_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_from_baseline_0012_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\airline_observability_smoke_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\baseline_0000_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\baseline_0001_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\baseline_0002_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\observability_from_baseline_0000_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\observability_from_baseline_0001_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\observability_from_baseline_0002_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\observability_from_baseline_0003_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\observability_from_baseline_0004_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\observability_from_baseline_0005_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\observability_smoke_from_baseline_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\smoke_live_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\smoke_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_baseline_0000_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_baseline_0001_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_baseline_0002_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_baseline_smoke_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0000_retry_provider_error_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0000_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0001_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0002_retry_provider_error_round2_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0002_retry_provider_error_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0002_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0003_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0004_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0005_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0006_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_from_baseline_0007_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_smoke_retry_provider_error_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyz_gpt55_airline_observability_smoke_status.jsonl', '<PROJECT_ROOT>\\runs\\schema_mutation\\phase5\\status\\wyzai_runner_smoke_status.jsonl']
- raw rows: 3537
- latest rows: 3260
- fake rows excluded: 4
- warnings: ['excluded 4 local_fake smoke rows', 'excluded 38 smoke rows']

## Baseline Selection
| env | model | provider | ok | baseline success | success rate | provider errors | timeout |
|---|---|---|---:|---:|---:|---:|---:|
| airline | dashscope/glm-5.1 | dashscope | 150 | 76 | 0.507 | 0 | 0 |
| airline | dashscope/kimi-k2.6 | dashscope | 150 | 73 | 0.487 | 0 | 0 |
| airline | dashscope/qwen-max | dashscope | 149 | 29 | 0.195 | 1 | 0 |
| airline | deepseek/deepseek-v4-flash | deepseek | 150 | 80 | 0.533 | 0 | 0 |
| airline | wyzlab/gpt-5.5 | wyzlab | 150 | 79 | 0.527 | 0 | 0 |
| retail | dashscope/glm-5.1 | dashscope | 60 | 32 | 0.533 | 0 | 0 |
| retail | dashscope/kimi-k2.6 | dashscope | 60 | 26 | 0.433 | 0 | 0 |
| retail | dashscope/qwen-max | dashscope | 60 | 24 | 0.400 | 0 | 0 |
| retail | deepseek/deepseek-v4-flash | deepseek | 60 | 23 | 0.383 | 0 | 0 |
| retail | wyzlab/gpt-5.5 | wyzlab | 0 | 0 | NA | 60 | 0 |

## Observability Gradient
| env | model | level | paired | success | mean drop | recovery success | visible error | hidden violation |
|---|---|---|---:|---:|---:|---:|---:|---:|
| airline | dashscope/glm-5.1 | O0_silent | 76 | 0.553 | 0.447 | 0.000 | 0.000 | 0.421 |
| airline | dashscope/glm-5.1 | O1_generic_error | 76 | 0.842 | 0.158 | 0.079 | 0.461 | 0.000 |
| airline | dashscope/glm-5.1 | O2_policy_error | 76 | 0.908 | 0.092 | 0.092 | 0.461 | 0.000 |
| airline | dashscope/glm-5.1 | O3_structured_policy_error | 76 | 0.882 | 0.118 | 0.066 | 0.447 | 0.000 |
| airline | dashscope/glm-5.1 | O4_migration_note | 76 | 0.855 | 0.145 | 0.079 | 0.461 | 0.000 |
| airline | dashscope/kimi-k2.6 | O0_silent | 73 | 0.548 | 0.452 | 0.000 | 0.000 | 0.356 |
| airline | dashscope/kimi-k2.6 | O1_generic_error | 73 | 0.932 | 0.068 | 0.123 | 0.370 | 0.000 |
| airline | dashscope/kimi-k2.6 | O2_policy_error | 73 | 0.877 | 0.123 | 0.110 | 0.411 | 0.000 |
| airline | dashscope/kimi-k2.6 | O3_structured_policy_error | 73 | 0.890 | 0.110 | 0.068 | 0.356 | 0.000 |
| airline | dashscope/kimi-k2.6 | O4_migration_note | 73 | 0.890 | 0.110 | 0.096 | 0.370 | 0.000 |
| airline | dashscope/qwen-max | O0_silent | 29 | 0.414 | 0.586 | 0.000 | 0.000 | 0.483 |
| airline | dashscope/qwen-max | O1_generic_error | 29 | 0.552 | 0.448 | 0.138 | 0.552 | 0.000 |
| airline | dashscope/qwen-max | O2_policy_error | 29 | 0.793 | 0.207 | 0.207 | 0.586 | 0.000 |
| airline | dashscope/qwen-max | O3_structured_policy_error | 29 | 0.690 | 0.310 | 0.172 | 0.552 | 0.000 |
| airline | dashscope/qwen-max | O4_migration_note | 29 | 0.655 | 0.345 | 0.241 | 0.655 | 0.000 |
| airline | deepseek/deepseek-v4-flash | O0_silent | 80 | 0.562 | 0.438 | 0.000 | 0.000 | 0.412 |
| airline | deepseek/deepseek-v4-flash | O1_generic_error | 80 | 0.850 | 0.150 | 0.087 | 0.400 | 0.000 |
| airline | deepseek/deepseek-v4-flash | O2_policy_error | 80 | 0.825 | 0.175 | 0.062 | 0.412 | 0.000 |
| airline | deepseek/deepseek-v4-flash | O3_structured_policy_error | 80 | 0.850 | 0.150 | 0.075 | 0.412 | 0.000 |
| airline | deepseek/deepseek-v4-flash | O4_migration_note | 80 | 0.863 | 0.138 | 0.100 | 0.425 | 0.000 |
| airline | wyzlab/gpt-5.5 | O0_silent | 79 | 0.532 | 0.468 | 0.000 | 0.000 | 0.405 |
| airline | wyzlab/gpt-5.5 | O1_generic_error | 79 | 0.873 | 0.127 | 0.101 | 0.418 | 0.000 |
| airline | wyzlab/gpt-5.5 | O2_policy_error | 79 | 0.886 | 0.114 | 0.114 | 0.430 | 0.000 |
| airline | wyzlab/gpt-5.5 | O3_structured_policy_error | 79 | 0.835 | 0.165 | 0.076 | 0.405 | 0.000 |
| airline | wyzlab/gpt-5.5 | O4_migration_note | 79 | 0.924 | 0.076 | 0.076 | 0.405 | 0.000 |
| retail | dashscope/glm-5.1 | O0_silent | 32 | 0.406 | 0.594 | 0.000 | 0.000 | 0.562 |
| retail | dashscope/glm-5.1 | O1_generic_error | 32 | 0.781 | 0.219 | 0.094 | 0.594 | 0.000 |
| retail | dashscope/glm-5.1 | O2_policy_error | 32 | 0.875 | 0.125 | 0.125 | 0.625 | 0.000 |
| retail | dashscope/glm-5.1 | O3_structured_policy_error | 32 | 0.875 | 0.125 | 0.094 | 0.625 | 0.000 |
| retail | dashscope/glm-5.1 | O4_migration_note | 32 | 0.844 | 0.156 | 0.000 | 0.531 | 0.000 |
| retail | dashscope/kimi-k2.6 | O0_silent | 26 | 0.500 | 0.500 | 0.000 | 0.000 | 0.500 |
| retail | dashscope/kimi-k2.6 | O1_generic_error | 26 | 0.846 | 0.154 | 0.038 | 0.500 | 0.000 |
| retail | dashscope/kimi-k2.6 | O2_policy_error | 26 | 0.808 | 0.192 | 0.038 | 0.500 | 0.000 |
| retail | dashscope/kimi-k2.6 | O3_structured_policy_error | 26 | 0.846 | 0.154 | 0.038 | 0.500 | 0.000 |
| retail | dashscope/kimi-k2.6 | O4_migration_note | 26 | 0.846 | 0.154 | 0.038 | 0.462 | 0.000 |
| retail | dashscope/qwen-max | O0_silent | 24 | 0.167 | 0.833 | 0.000 | 0.000 | 0.625 |
| retail | dashscope/qwen-max | O1_generic_error | 24 | 0.875 | 0.125 | 0.083 | 0.583 | 0.000 |
| retail | dashscope/qwen-max | O2_policy_error | 24 | 0.667 | 0.333 | 0.083 | 0.583 | 0.000 |
| retail | dashscope/qwen-max | O3_structured_policy_error | 24 | 0.750 | 0.250 | 0.083 | 0.542 | 0.000 |
| retail | dashscope/qwen-max | O4_migration_note | 24 | 0.833 | 0.167 | 0.125 | 0.625 | 0.000 |
| retail | deepseek/deepseek-v4-flash | O0_silent | 23 | 0.565 | 0.435 | 0.000 | 0.000 | 0.435 |
| retail | deepseek/deepseek-v4-flash | O1_generic_error | 23 | 0.957 | 0.043 | 0.043 | 0.478 | 0.000 |
| retail | deepseek/deepseek-v4-flash | O2_policy_error | 23 | 0.870 | 0.130 | 0.000 | 0.435 | 0.000 |
| retail | deepseek/deepseek-v4-flash | O3_structured_policy_error | 23 | 0.913 | 0.087 | 0.000 | 0.435 | 0.000 |
| retail | deepseek/deepseek-v4-flash | O4_migration_note | 23 | 0.913 | 0.087 | 0.000 | 0.435 | 0.000 |

## B/D Mutation Summary
| env | model | class | mutation | protocol | paired | success | visible error |
|---|---|---|---|---|---:|---:|---:|
| NA | NA | NA | NA | NA | 0 | NA | NA |
