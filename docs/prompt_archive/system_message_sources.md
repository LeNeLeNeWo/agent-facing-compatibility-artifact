# System Message and Runtime Text Sources

## Agent System Message

- Source: TAU-BENCH `ToolCallingAgent.solve`.
- Content: `isolated_env.wiki`.
- Code path:
  - `code/schema_mutation/runner.py::run`
  - `tau_bench.agents.tool_calling_agent.ToolCallingAgent.solve`

## User Simulator System Message

- Source: TAU-BENCH `LLMUserSimulationEnv.build_system_prompt(instruction)`.
- Content: static template plus the task instruction, if present.
- Code path:
  - `code/schema_mutation/runner.py::run`
  - `tau_bench.envs.get_env(...)`
  - `tau_bench.envs.user.load_user(...)`
  - `tau_bench.envs.user.LLMUserSimulationEnv.build_system_prompt(...)`

## Observability-Gradient Runtime Text

- O0: no visible runtime error; hidden oracle forces reward zero if the new
  business rule is violated.
- O1: `Operation failed. Request cannot be completed.`
- O2: `Policy violation: this request does not satisfy the updated API business
  policy. <drift>`
- O3/O4 runtime error: JSON object from
  `structured_policy_error_text(intent, action_name, drift)`.
- O4 pre-action signal: `Migration note: The <tool> API has updated its business
  policy. <drift>`

## Runtime Metadata

The prompt/message construction is separate from runtime metadata. Formal Phase
5 records use:

- `max_num_steps=30`
- `timeout_seconds=600`
- `temperature=0.0` where supported
- `env_user_model=dashscope/qwen-flash`
- `env_user_provider=dashscope`
