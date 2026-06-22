# Phase 10C Non-Obviousness Formal Summary

- Planned cells: 288
- Completed status cells: 288
- OK cells: 286
- Missing cells: 0
- Extra status cells: 0
- Status counts: failed=1, ok=286, timeout=1
- Completed shards: 8
- Formal status complete: True
- Formal all OK: False
- Formal completed cleanly: False
- Rule leakage detected: False
- Retry-needed cells: 2
- Phase 10D analysis ready: True
- Phase 10D caveat: exclude or retry non-ok infrastructure rows before final statistical claims

## By Condition

| group | planned | completed | ok | status counts | success | hidden violation | visible policy error |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| O0_increased_reasoning_budget | 96 | 96 | 96 | ok=96 | 3.1% | 95.8% | 0.0% |
| O0_reflection_scaffold | 96 | 96 | 95 | failed=1, ok=95 | 6.3% | 92.6% | 0.0% |
| rule_in_tool_preamble_upper_bound | 96 | 96 | 95 | ok=95, timeout=1 | 74.7% | 0.0% | 96.8% |

## By Domain

| group | planned | completed | ok | status counts | success | hidden violation | visible policy error |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| airline | 174 | 174 | 172 | failed=1, ok=172, timeout=1 | 25.0% | 62.2% | 31.4% |
| retail | 114 | 114 | 114 | ok=114 | 32.5% | 64.0% | 33.3% |

## By Model

| group | planned | completed | ok | status counts | success | hidden violation | visible policy error |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| dashscope/glm-5.1 | 75 | 75 | 74 | ok=74, timeout=1 | 29.7% | 63.5% | 32.4% |
| dashscope/kimi-k2.6 | 69 | 69 | 69 | ok=69 | 31.9% | 62.3% | 31.9% |
| dashscope/qwen-max | 78 | 78 | 77 | failed=1, ok=77 | 28.6% | 59.7% | 31.2% |
| deepseek/deepseek-v4-flash | 66 | 66 | 66 | ok=66 | 21.2% | 66.7% | 33.3% |

## By Semantic Class

| group | planned | completed | ok | status counts | success | hidden violation | visible policy error |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| C1 | 81 | 81 | 81 | ok=81 | 27.2% | 63.0% | 33.3% |
| C2 | 57 | 57 | 57 | ok=57 | 31.6% | 61.4% | 31.6% |
| C3 | 69 | 69 | 67 | failed=1, ok=67, timeout=1 | 29.9% | 62.7% | 31.3% |
| C4 | 81 | 81 | 81 | ok=81 | 24.7% | 64.2% | 32.1% |

## Pattern Flags

- Rule-in-prompt upper bound improves: True
- O0 reasoning/reflection still struggles: True

## Non-OK Rows

- p10_nonobv_a1a33c598319: status=failed condition=O0_reflection_scaffold model=dashscope/qwen-max env=airline class=C3 file=nonobviousness_0003_status.jsonl
- p10_nonobv_8bc60a8c512f: status=timeout condition=rule_in_tool_preamble_upper_bound model=dashscope/glm-5.1 env=airline class=C3 file=nonobviousness_0005_status.jsonl
