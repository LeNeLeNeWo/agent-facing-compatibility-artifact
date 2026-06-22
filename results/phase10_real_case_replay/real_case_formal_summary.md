# Phase 10F-R1 Real-Changelog-Grounded Replay Formal Summary

- Selected cases: real_c1_unit_scale_0a2066fde082, real_c4_business_rule_323e42cd6611
- Cells planned: 72
- Cells with latest terminal status: 72
- Latest-cell status counts: failed=2, ok=70
- Provider errors: 0
- Timeouts: 0
- Failed rows: 2
- Rule leakage rows: 0
- Real third-party API call rows: 0
- Failed/provider/timeout rows are excluded from success and hidden-violation rates, and are not counted as agent semantic failures.

## By Condition

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline old API | 24 | 24/24 (100.0%) | 0/24 (0.0%) | 0/24 (0.0%) | ok=24 |
| Evolved O0 silent | 23 | 0/23 (0.0%) | 23/23 (100.0%) | 0/23 (0.0%) | failed=1, ok=23 |
| Evolved visible feedback | 23 | 22/23 (95.7%) | 0/23 (0.0%) | 23/23 (100.0%) | failed=1, ok=23 |

## By Case

### real_c1_unit_scale_0a2066fde082

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline old API | 12 | 12/12 (100.0%) | 0/12 (0.0%) | 0/12 (0.0%) | ok=12 |
| Evolved O0 silent | 11 | 0/11 (0.0%) | 11/11 (100.0%) | 0/11 (0.0%) | failed=1, ok=11 |
| Evolved visible feedback | 12 | 11/12 (91.7%) | 0/12 (0.0%) | 12/12 (100.0%) | ok=12 |

### real_c4_business_rule_323e42cd6611

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| Baseline old API | 12 | 12/12 (100.0%) | 0/12 (0.0%) | 0/12 (0.0%) | ok=12 |
| Evolved O0 silent | 12 | 0/12 (0.0%) | 12/12 (100.0%) | 0/12 (0.0%) | ok=12 |
| Evolved visible feedback | 11 | 11/11 (100.0%) | 0/11 (0.0%) | 11/11 (100.0%) | failed=1, ok=11 |

## By Model

### dashscope/glm-5.1

| condition | ok N | success | hidden violation | visible rule exposed |
| --- | ---: | ---: | ---: | ---: |
| Baseline old API | 6 | 6/6 (100.0%) | 0/6 (0.0%) | 0/6 (0.0%) |
| Evolved O0 silent | 6 | 0/6 (0.0%) | 6/6 (100.0%) | 0/6 (0.0%) |
| Evolved visible feedback | 5 | 4/5 (80.0%) | 0/5 (0.0%) | 5/5 (100.0%) |

### dashscope/kimi-k2.6

| condition | ok N | success | hidden violation | visible rule exposed |
| --- | ---: | ---: | ---: | ---: |
| Baseline old API | 6 | 6/6 (100.0%) | 0/6 (0.0%) | 0/6 (0.0%) |
| Evolved O0 silent | 6 | 0/6 (0.0%) | 6/6 (100.0%) | 0/6 (0.0%) |
| Evolved visible feedback | 6 | 6/6 (100.0%) | 0/6 (0.0%) | 6/6 (100.0%) |

### dashscope/qwen-max

| condition | ok N | success | hidden violation | visible rule exposed |
| --- | ---: | ---: | ---: | ---: |
| Baseline old API | 6 | 6/6 (100.0%) | 0/6 (0.0%) | 0/6 (0.0%) |
| Evolved O0 silent | 6 | 0/6 (0.0%) | 6/6 (100.0%) | 0/6 (0.0%) |
| Evolved visible feedback | 6 | 6/6 (100.0%) | 0/6 (0.0%) | 6/6 (100.0%) |

### deepseek/deepseek-v4-flash

| condition | ok N | success | hidden violation | visible rule exposed |
| --- | ---: | ---: | ---: | ---: |
| Baseline old API | 6 | 6/6 (100.0%) | 0/6 (0.0%) | 0/6 (0.0%) |
| Evolved O0 silent | 5 | 0/5 (0.0%) | 5/5 (100.0%) | 0/5 (0.0%) |
| Evolved visible feedback | 6 | 6/6 (100.0%) | 0/6 (0.0%) | 6/6 (100.0%) |

## Statistical Checks

Bootstrap success-rate CIs:
- Baseline old API: 100.0% [100.0%, 100.0%], n=24
- Evolved O0 silent: 0.0% [0.0%, 0.0%], n=23
- Evolved visible feedback: 95.7% [87.0%, 100.0%], n=23

Bootstrap success-rate differences:
- baseline_old_api_vs_evolved_o0_silent: 100.0% [100.0%, 100.0%]
- baseline_old_api_vs_evolved_visible_feedback: 4.3% [0.0%, 13.0%]
- evolved_o0_silent_vs_evolved_visible_feedback: -95.7% [-100.0%, -87.0%]

Bootstrap hidden-violation-rate differences:
- baseline_old_api_vs_evolved_o0_silent: -100.0% [-100.0%, -100.0%]
- baseline_old_api_vs_evolved_visible_feedback: 0.0% [0.0%, 0.0%]
- evolved_o0_silent_vs_evolved_visible_feedback: 100.0% [100.0%, 100.0%]

Fisher exact / chi-square tests on success:
- baseline_old_api_vs_evolved_o0_silent: Fisher p=6.202e-14, chi-square p=7.099e-12, table=[[24, 0], [0, 23]]
- baseline_old_api_vs_evolved_visible_feedback: Fisher p=0.4894, chi-square p=0.3018, table=[[24, 0], [22, 1]]
- evolved_o0_silent_vs_evolved_visible_feedback: Fisher p=5.83e-12, chi-square p=8.382e-11, table=[[0, 23], [22, 1]]

Fisher exact / chi-square tests on hidden violations:
- baseline_old_api_vs_evolved_o0_silent: Fisher p=6.202e-14, chi-square p=7.099e-12, table=[[0, 24], [23, 0]]
- baseline_old_api_vs_evolved_visible_feedback: Fisher p=1, chi-square p=n/a, table=[[0, 24], [0, 23]]
- evolved_o0_silent_vs_evolved_visible_feedback: Fisher p=2.429e-13, chi-square p=1.183e-11, table=[[23, 0], [0, 23]]

## Non-OK Rows

- phase10f_r1::real_c1_unit_scale_0a2066fde082::evolved_o0_silent::deepseek-deepseek-v4-flash::s2: status=failed, condition=evolved_o0_silent, model=deepseek/deepseek-v4-flash, seed=2, deterministic_oracle_ok=False
- phase10f_r1::real_c4_business_rule_323e42cd6611::evolved_visible_feedback::dashscope-glm-5_1::s2: status=failed, condition=evolved_visible_feedback, model=dashscope/glm-5.1, seed=2, deterministic_oracle_ok=False

## Integrity

- No real Stripe/GitHub API calls were made by the deterministic local wrappers.
- O0 silent rows did not expose the changed rule through visible feedback.
- Visible-feedback rows exposed the changed rule through runtime feedback.
- Provider errors/timeouts/failed rows are not counted as agent failures.
- This is a formal real-changelog-grounded replay result, not a production incident frequency estimate.
