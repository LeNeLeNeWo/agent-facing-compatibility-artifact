# Phase 10A Non-Obviousness Control Plan

No API calls were run. This plan tests whether silent semantic drift can be solved by more reasoning without exposing the changed rule.

- Baseline O0 hidden-positive reference cells: 96
- Planned cells: 288
- Runner-ready cells: 192
- Rows requiring runner prompt hook: 96
- Expected API calls if all conditions run: 288
- Expected API calls for runner-ready subset: 192
- Smoke shard: `runs\schema_mutation\phase10\nonobviousness\shards\nonobviousness_smoke.jsonl`

## By Condition
- O0_increased_reasoning_budget: 96
- O0_reflection_scaffold: 96
- rule_in_tool_preamble_upper_bound: 96

## By Domain
- airline: 174
- retail: 114

## By Model
- dashscope/glm-5.1: 75
- dashscope/kimi-k2.6: 69
- dashscope/qwen-max: 78
- deepseek/deepseek-v4-flash: 66

## By Semantic Class
- C1: 81
- C2: 57
- C3: 69
- C4: 81

## How This Addresses the Obviousness Critique

The matched design keeps the same O0 hidden semantic drift cells and varies only reasoning budget, reflection scaffolding, or explicit rule visibility. If larger budgets and reflection do not recover while rule visibility does, the failure is not merely weak reasoning; it is missing semantic observability.

## Stop Rules
- provider_error >= 5 in one shard
- timeout >= 5 in one shard
- failed >= 10 in one shard
- fake_run appears
- GPT/WYZ/Grok appears
- schema_changed=true appears
- baseline_success=false appears

Note: Reflection scaffold rows are planned but require a runner prompt hook before execution.
