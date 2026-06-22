# AFC-Gate Evaluation Summary

Inputs:
- `<PROJECT_ROOT>\runs\schema_mutation\paired_day10_c4a_c4b_deepseek.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\paired_day11_c4a_c4b_qwen_kimi.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\paired_day16_airline_deepseek_s0_unused_control.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\paired_day16_airline_deepseek_s12_c4a_c4b.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\paired_day16_airline_qwen_max_c4a_c4b.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\observability_from_baseline_0000_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\observability_from_baseline_0001_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\observability_from_baseline_0002_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\observability_from_baseline_0003_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\observability_from_baseline_0004_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\observability_from_baseline_0005_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0000_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0001_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0002_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0003_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0004_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0005_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0006_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0007_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0008_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0009_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0010_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0011_status.jsonl`
- `<PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0012_status.jsonl`

Warnings:
- deduped_phase5_retry_rows: <PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0000_status.jsonl (52)
- deduped_phase5_retry_rows: <PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0004_status.jsonl (1)
- deduped_phase5_retry_rows: <PROJECT_ROOT>\runs\schema_mutation\phase5\status\airline_observability_from_baseline_0007_status.jsonl (1)
- split_day6 artifacts detected but skipped: they are not paired baseline/mutation rows

| Method | Recall | Silent Recall | Precision | FPR | Tests Run | Cost vs Exhaustive | Notes |
|---|---:|---:|---:|---:|---:|---:|---|
| SchemaCheckerOnly | 0.000 | 0.000 | NA | 0.000 | 0 | 0.000 | blocked_schema_compatible=0; lift=0.000; warning_quality=NA |
| RandomReplayGate | 0.004 | 0.008 | 0.500 | 0.001 | 10 | 0.005 | blocked_schema_compatible=2; lift=0.004; warning_quality=1.000 |
| UsedToolReplayGate | 0.000 | 0.000 | 0.000 | 0.005 | 10 | 0.005 | blocked_schema_compatible=0; lift=0.000; warning_quality=1.000 |
| IntentAlignedReplayGate | 0.000 | 0.000 | 0.000 | 0.005 | 10 | 0.005 | blocked_schema_compatible=0; lift=0.000; warning_quality=1.000 |
| AFCGate | 0.523 | 0.996 | 0.557 | 0.134 | 10 | 0.005 | blocked_schema_compatible=0; lift=0.523; warning_quality=0.573 |
| ExhaustiveReplayOracle | 0.804 | 0.913 | 0.399 | 0.389 | 1987 | 1.000 | blocked_schema_compatible=389; lift=0.804; warning_quality=1.000 |
