# Number Reconciliation Report

Offline paper/artifact number audit. No experiments or model APIs were run.

## Paper Number Presence
- `strict_schema_client`: OK
- `relaxed_yp`: OK
- `exposure_control`: OK
- `observability`: OK
- `phase8c`: OK
- `phase10_corpus`: OK
- `phase10_replay`: OK
- `phase10_nonobvious`: OK

## Artifact-Derived Values
```json
{
  "corpus_provider_count": 9,
  "corpus_schema_invisible_c": 61,
  "corpus_total_entries": 151,
  "nonobvious_by_condition": {
    "O0_increased_reasoning_budget": {
      "hidden_violation_n": 92,
      "ok": 96,
      "success_n": 3
    },
    "O0_reflection_scaffold": {
      "hidden_violation_n": 88,
      "ok": 95,
      "success_n": 6
    },
    "rule_in_tool_preamble_upper_bound": {
      "hidden_violation_n": 0,
      "ok": 95,
      "success_n": 71
    }
  },
  "nonobvious_ok_cells": 286,
  "nonobvious_planned_cells": 288,
  "nonobvious_status_counts": {
    "failed": 1,
    "ok": 286,
    "timeout": 1
  },
  "oracle_baseline_violation_rate": 0.0,
  "oracle_suspicious_count": 0,
  "oracle_total_samples": 180,
  "real_replay_all_status_records": 72,
  "real_replay_by_condition": {
    "baseline_old_api": {
      "hidden_violation_n": 0,
      "ok_n": 24,
      "success_n": 24
    },
    "evolved_o0_silent": {
      "hidden_violation_n": 23,
      "ok_n": 23,
      "success_n": 0
    },
    "evolved_visible_feedback": {
      "hidden_violation_n": 0,
      "ok_n": 23,
      "success_n": 22
    }
  },
  "real_replay_status_counts": {
    "failed": 2,
    "ok": 70
  }
}
```

## Phrase Checks
- `ambiguous_c1_or`: False
- `human_kappa`: False
- `production_frequency_claim`: True
- `production_incident_claim`: True
- `gpt_table_ref`: False

## Recommendation
- Keep the 288-cell control wording, but ensure Table II or nearby text explains that two non-ok infrastructure rows are excluded from denominators.