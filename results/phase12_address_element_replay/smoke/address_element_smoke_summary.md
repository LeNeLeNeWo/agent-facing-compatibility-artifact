# Phase 12J Address Element Replay Summary

- Case: `stripe_address_element_state_format_20260325`
- Cells planned: 6
- Cells with latest terminal status: 6
- Latest-cell status counts: ok=6
- All status records retained: 12 ({'ok': 12})
- Raw records retained: 12
- Deterministic oracle worked for ok rows: True
- Rule leakage rows: 0
- Real third-party API call rows: 0
- Formal/integration readiness signal: True (Baseline succeeds, silent evolved condition hidden-violates, and visible condition recovers.)

## By Condition

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 2 | 2/2 (100.0%) | 0/2 (0.0%) | 0/2 (0.0%) | {'ok': 2} |
| evolved_o0_silent | 2 | 0/2 (0.0%) | 2/2 (100.0%) | 0/2 (0.0%) | {'ok': 2} |
| evolved_visible_feedback | 2 | 2/2 (100.0%) | 0/2 (0.0%) | 2/2 (100.0%) | {'ok': 2} |

## By Model

### dashscope/qwen-max

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 1 | 1/1 (100.0%) | 0/1 (0.0%) | 0/1 (0.0%) | {'ok': 1} |
| evolved_o0_silent | 1 | 0/1 (0.0%) | 1/1 (100.0%) | 0/1 (0.0%) | {'ok': 1} |
| evolved_visible_feedback | 1 | 1/1 (100.0%) | 0/1 (0.0%) | 1/1 (100.0%) | {'ok': 1} |

### deepseek/deepseek-v4-flash

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 1 | 1/1 (100.0%) | 0/1 (0.0%) | 0/1 (0.0%) | {'ok': 1} |
| evolved_o0_silent | 1 | 0/1 (0.0%) | 1/1 (100.0%) | 0/1 (0.0%) | {'ok': 1} |
| evolved_visible_feedback | 1 | 1/1 (100.0%) | 0/1 (0.0%) | 1/1 (100.0%) | {'ok': 1} |

## By Seed

### seed=0

| condition | ok N | success | hidden violation | visible rule exposed | status counts |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline_old_api | 2 | 2/2 (100.0%) | 0/2 (0.0%) | 0/2 (0.0%) | {'ok': 2} |
| evolved_o0_silent | 2 | 0/2 (0.0%) | 2/2 (100.0%) | 0/2 (0.0%) | {'ok': 2} |
| evolved_visible_feedback | 2 | 2/2 (100.0%) | 0/2 (0.0%) | 2/2 (100.0%) | {'ok': 2} |

## Statistical Checks

Bootstrap success-rate CIs:
- baseline_old_api: 100.0% CI [100.0%, 100.0%], n=2
- evolved_o0_silent: 0.0% CI [0.0%, 0.0%], n=2
- evolved_visible_feedback: 100.0% CI [100.0%, 100.0%], n=2

Bootstrap hidden-violation-rate CIs:
- baseline_old_api: 0.0% CI [0.0%, 0.0%], n=2
- evolved_o0_silent: 100.0% CI [100.0%, 100.0%], n=2
- evolved_visible_feedback: 0.0% CI [0.0%, 0.0%], n=2

Bootstrap success-rate differences:
- baseline_old_api_vs_evolved_o0_silent: 100.0% CI [100.0%, 100.0%]
- evolved_o0_silent_vs_evolved_visible_feedback: -100.0% CI [-100.0%, -100.0%]
- baseline_old_api_vs_evolved_visible_feedback: 0.0% CI [0.0%, 0.0%]

Bootstrap hidden-violation-rate differences:
- baseline_old_api_vs_evolved_o0_silent: -100.0% CI [-100.0%, -100.0%]
- evolved_o0_silent_vs_evolved_visible_feedback: 100.0% CI [100.0%, 100.0%]
- baseline_old_api_vs_evolved_visible_feedback: 0.0% CI [0.0%, 0.0%]

Fisher exact / chi-square tests on success:
- baseline_old_api_vs_evolved_o0_silent: Fisher p=0.3333, chi-square p=0.0455, table=[[2, 0], [0, 2]]
- evolved_o0_silent_vs_evolved_visible_feedback: Fisher p=0.3333, chi-square p=0.0455, table=[[0, 2], [2, 0]]
- baseline_old_api_vs_evolved_visible_feedback: Fisher p=1, chi-square p=n/a, table=[[2, 0], [2, 0]]

Fisher exact / chi-square tests on hidden violations:
- baseline_old_api_vs_evolved_o0_silent: Fisher p=0.3333, chi-square p=0.0455, table=[[0, 2], [2, 0]]
- evolved_o0_silent_vs_evolved_visible_feedback: Fisher p=0.3333, chi-square p=0.0455, table=[[2, 0], [0, 2]]
- baseline_old_api_vs_evolved_visible_feedback: Fisher p=1, chi-square p=n/a, table=[[0, 2], [0, 2]]

## Integrity Notes

- The wrapper is deterministic and local; it does not call Stripe.
- Provider_error/timeout/failed rows are not counted as agent semantic failures.
- This is a supplemental public-changelog replay case, not a production incident or production-frequency estimate.
