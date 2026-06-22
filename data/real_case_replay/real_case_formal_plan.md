# Phase 10F-R1 Real-Case Replay Formal Plan

This plan expands the successful Phase 10E-R1 smoke cases into a formal real-changelog-grounded replay. It uses deterministic local wrappers only; no real Stripe or GitHub API calls are permitted.

- Planned cells: 72
- Selected cases: real_c1_unit_scale_0a2066fde082, real_c4_business_rule_323e42cd6611
- Models: deepseek/deepseek-v4-flash, dashscope/qwen-max, dashscope/kimi-k2.6, dashscope/glm-5.1
- Seeds: 0, 1, 2
- Conditions: baseline_old_api, evolved_o0_silent, evolved_visible_feedback
- Cell formula: selected_cases x 4 models x 3 seeds x 3 conditions
- Maximum allowed cells for this phase: 108

## Distribution

### Cases

- `real_c1_unit_scale_0a2066fde082`: 36
- `real_c4_business_rule_323e42cd6611`: 36

### Conditions

- `baseline_old_api`: 24
- `evolved_o0_silent`: 24
- `evolved_visible_feedback`: 24

### Models

- `dashscope/glm-5.1`: 18
- `dashscope/kimi-k2.6`: 18
- `dashscope/qwen-max`: 18
- `deepseek/deepseek-v4-flash`: 18

### Seeds

- `0`: 24
- `1`: 24
- `2`: 24

## Integrity Constraints

- `real_third_party_api_allowed` is false for every cell.
- `fake_run` is false for every cell.
- `tool_schema_unchanged` is true for every cell.
- O0 silent cells inherit the smoke prompt template and do not expose the changed rule through visible feedback.
- Visible-feedback cells expose the changed rule through runtime feedback, not through the hidden oracle.
