# Phase 12J Address Element Replay Summary

- Case: `stripe_address_element_state_format_20260325`
- Cells planned: 36
- Cells with latest terminal status: 36
- Latest-cell status counts: ok=36
- All status records retained: 36 ({'ok': 36})
- Raw records retained: 36
- Deterministic oracle worked for ok rows: True
- Rule leakage rows: 0
- Real third-party API call rows: 0
- Formal/integration readiness signal: True (Baseline succeeds, silent evolved condition hidden-violates, and visible condition recovers.)

## By Condition

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 12 | 12/12 (100.0%) | 0/12 (0.0%) | 0/12 (0.0%) | {'ok': 12} |
| evolved_o0_silent | 12 | 6/12 (50.0%) | 6/12 (50.0%) | 0/12 (0.0%) | {'ok': 12} |
| evolved_visible_feedback | 12 | 12/12 (100.0%) | 0/12 (0.0%) | 12/12 (100.0%) | {'ok': 12} |

## By Model

### dashscope/glm-5.1

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 3 | 3/3 (100.0%) | 0/3 (0.0%) | 0/3 (0.0%) | {'ok': 3} |
| evolved_o0_silent | 3 | 3/3 (100.0%) | 0/3 (0.0%) | 0/3 (0.0%) | {'ok': 3} |
| evolved_visible_feedback | 3 | 3/3 (100.0%) | 0/3 (0.0%) | 3/3 (100.0%) | {'ok': 3} |

### dashscope/kimi-k2.6

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 3 | 3/3 (100.0%) | 0/3 (0.0%) | 0/3 (0.0%) | {'ok': 3} |
| evolved_o0_silent | 3 | 0/3 (0.0%) | 3/3 (100.0%) | 0/3 (0.0%) | {'ok': 3} |
| evolved_visible_feedback | 3 | 3/3 (100.0%) | 0/3 (0.0%) | 3/3 (100.0%) | {'ok': 3} |

### dashscope/qwen-max

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 3 | 3/3 (100.0%) | 0/3 (0.0%) | 0/3 (0.0%) | {'ok': 3} |
| evolved_o0_silent | 3 | 0/3 (0.0%) | 3/3 (100.0%) | 0/3 (0.0%) | {'ok': 3} |
| evolved_visible_feedback | 3 | 3/3 (100.0%) | 0/3 (0.0%) | 3/3 (100.0%) | {'ok': 3} |

### deepseek/deepseek-v4-flash

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 3 | 3/3 (100.0%) | 0/3 (0.0%) | 0/3 (0.0%) | {'ok': 3} |
| evolved_o0_silent | 3 | 3/3 (100.0%) | 0/3 (0.0%) | 0/3 (0.0%) | {'ok': 3} |
| evolved_visible_feedback | 3 | 3/3 (100.0%) | 0/3 (0.0%) | 3/3 (100.0%) | {'ok': 3} |

## By Seed

### seed=0

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 4 | 4/4 (100.0%) | 0/4 (0.0%) | 0/4 (0.0%) | {'ok': 4} |
| evolved_o0_silent | 4 | 2/4 (50.0%) | 2/4 (50.0%) | 0/4 (0.0%) | {'ok': 4} |
| evolved_visible_feedback | 4 | 4/4 (100.0%) | 0/4 (0.0%) | 4/4 (100.0%) | {'ok': 4} |

### seed=1

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 4 | 4/4 (100.0%) | 0/4 (0.0%) | 0/4 (0.0%) | {'ok': 4} |
| evolved_o0_silent | 4 | 2/4 (50.0%) | 2/4 (50.0%) | 0/4 (0.0%) | {'ok': 4} |
| evolved_visible_feedback | 4 | 4/4 (100.0%) | 0/4 (0.0%) | 4/4 (100.0%) | {'ok': 4} |

### seed=2

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 4 | 4/4 (100.0%) | 0/4 (0.0%) | 0/4 (0.0%) | {'ok': 4} |
| evolved_o0_silent | 4 | 2/4 (50.0%) | 2/4 (50.0%) | 0/4 (0.0%) | {'ok': 4} |
| evolved_visible_feedback | 4 | 4/4 (100.0%) | 0/4 (0.0%) | 4/4 (100.0%) | {'ok': 4} |

## Statistical Checks

Bootstrap success-rate CIs:
- baseline_old_api: 100.0% CI [100.0%, 100.0%], n=12
- evolved_o0_silent: 50.0% CI [25.0%, 75.0%], n=12
- evolved_visible_feedback: 100.0% CI [100.0%, 100.0%], n=12

Bootstrap hidden-violation-rate CIs:
- baseline_old_api: 0.0% CI [0.0%, 0.0%], n=12
- evolved_o0_silent: 50.0% CI [25.0%, 75.0%], n=12
- evolved_visible_feedback: 0.0% CI [0.0%, 0.0%], n=12

Bootstrap success-rate differences:
- baseline_old_api_vs_evolved_o0_silent: 50.0% CI [25.0%, 75.0%]
- evolved_o0_silent_vs_evolved_visible_feedback: -50.0% CI [-75.0%, -25.0%]
- baseline_old_api_vs_evolved_visible_feedback: 0.0% CI [0.0%, 0.0%]

Bootstrap hidden-violation-rate differences:
- baseline_old_api_vs_evolved_o0_silent: -50.0% CI [-75.0%, -25.0%]
- evolved_o0_silent_vs_evolved_visible_feedback: 50.0% CI [25.0%, 75.0%]
- baseline_old_api_vs_evolved_visible_feedback: 0.0% CI [0.0%, 0.0%]

Fisher exact / chi-square tests on success:
- baseline_old_api_vs_evolved_o0_silent: Fisher p=0.01373, chi-square p=0.004678, table=[[12, 0], [6, 6]]
- evolved_o0_silent_vs_evolved_visible_feedback: Fisher p=0.01373, chi-square p=0.004678, table=[[6, 6], [12, 0]]
- baseline_old_api_vs_evolved_visible_feedback: Fisher p=1, chi-square p=n/a, table=[[12, 0], [12, 0]]

Fisher exact / chi-square tests on hidden violations:
- baseline_old_api_vs_evolved_o0_silent: Fisher p=0.01373, chi-square p=0.004678, table=[[0, 12], [6, 6]]
- evolved_o0_silent_vs_evolved_visible_feedback: Fisher p=0.01373, chi-square p=0.004678, table=[[6, 6], [0, 12]]
- baseline_old_api_vs_evolved_visible_feedback: Fisher p=1, chi-square p=n/a, table=[[0, 12], [0, 12]]

## Integrity Notes

- The wrapper is deterministic and local; it does not call Stripe.
- Provider_error/timeout/failed rows are not counted as agent semantic failures.
- This is a supplemental public-changelog replay case, not a production incident or production-frequency estimate.
