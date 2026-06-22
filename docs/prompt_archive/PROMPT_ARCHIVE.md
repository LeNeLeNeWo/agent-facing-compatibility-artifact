# Prompt Archive

Generated during Phase 6F on 2026-06-16. This archive is documentation only:
no model API calls, no shard execution, and no experiment reruns were performed.

## Summary

The current artifact package does not contain fully rendered per-cell message
arrays for the agent or user simulator. The archive therefore records the
source-code construction path, exact static templates that can be recovered from
the installed TAU-BENCH package, and the observability-specific injected text
templates used by the schema-mutation wrapper.

Exact standalone prompt text was not emitted as an artifact in the current run.
The archive records the source-code construction path and the metadata needed to
reproduce it. Future clean reruns should persist the fully rendered messages per
task/seed.

## Agent Prompt Construction

- Entry point: `code/schema_mutation/runner.py::run`.
- Environment construction: `tau_bench.envs.get_env(...)` is called with the
  configured environment, user strategy, user model, split, provider, and task
  index.
- Agent construction: `tau_bench.agents.tool_calling_agent.ToolCallingAgent` is
  instantiated in `code/schema_mutation/runner.py` with:
  - `tools_info=tools_info`
  - `wiki=isolated_env.wiki`
  - `model=<agent model>`
  - `provider="openai"` with LiteLLM routing patched to the configured provider
  - `temperature=0.0` in the formal runs
- TAU-BENCH agent message skeleton:
  - system message content is `isolated_env.wiki`
  - first user message content is the initial user-simulator observation returned
    by `env.reset(task_index=...)`
  - tool schemas are passed through the `tools=` argument to LiteLLM rather than
    inlined into a text prompt.
- Exact dynamic values not archived as standalone prompt text:
  - per-environment wiki text
  - per-task initial user-simulator observation
  - full rendered tool schema after mutation
  - subsequent assistant/tool/user messages in each trajectory

See `agent_prompt_construction.md` and `agent_system_prompt_template.txt`.

## User Simulator Prompt Construction

- User simulator model: `dashscope/qwen-flash`.
- User simulator provider: DashScope.
- User strategy in formal runs: TAU-BENCH `llm` strategy.
- Construction path:
  - `code/schema_mutation/batch_runner.py` default config sets
    `user_model=dashscope/qwen-flash` and `user_provider=dashscope`.
  - `code/schema_mutation/runner.py::run` passes those values into
    `tau_bench.envs.get_env(...)`.
  - TAU-BENCH `tau_bench.envs.user.load_user(...)` creates
    `LLMUserSimulationEnv`.
  - `LLMUserSimulationEnv.build_system_prompt(instruction)` renders the exact
    static user-simulator system prompt template with the task instruction.
- Exact static template recovered: yes, see
  `user_simulator_prompt_template.txt`.
- Exact rendered per-task simulator prompts were not persisted as standalone
  artifacts in the current run.

## System Messages and Mutation-Injected Text

- Agent system message source: `isolated_env.wiki`, passed as the first system
  message by `tau_bench.agents.tool_calling_agent.ToolCallingAgent.solve`.
- User simulator system message source:
  `tau_bench.envs.user.LLMUserSimulationEnv.build_system_prompt`.
- O4 migration-note source:
  `code/schema_mutation/c4_observability_modes.py::migration_note`, injected
  into the target tool description by `code/schema_mutation/runner.py`.
- O1 generic-error source:
  `code/schema_mutation/c4_observability_modes.py::generic_error_message`.
- O2 policy-error source:
  `code/schema_mutation/c4_observability_modes.py::policy_error_message`.
- O3 structured-error source:
  `code/schema_mutation/c4_observability_modes.py::structured_policy_error_text`.
- Runtime wrapper source:
  `code/schema_mutation/runner.py::_wrap_step_for_business_rules`.

## Exact vs Reconstructed

- Exact archived static template:
  - user simulator `LLMUserSimulationEnv.build_system_prompt` template.
  - TAU-BENCH agent message skeleton from `ToolCallingAgent.solve`.
  - O1/O2/O3/O4 observability text templates.
- Source-code construction path:
  - agent rendered messages, environment wiki, tool schema, and tool-call
    transcript are reconstructible from the TAU-BENCH environment and runner
    source but were not persisted as standalone per-cell message artifacts.
- Not archived:
  - fully rendered per-cell `agent_messages`
  - fully rendered per-cell `user_simulator_messages`
  - per-cell rendered tool schema snapshots

## Future Artifact Requirement

Future clean reruns should persist the following sidecar record for every formal
cell:

```json
{
  "cell_key": "...",
  "agent_messages": [],
  "user_simulator_messages": [],
  "tool_schema": {},
  "observability_level": "...",
  "rendered_migration_note": "...",
  "rendered_error_message": "..."
}
```

This would turn the current construction-path archive into a fully rendered
message archive without relying on package/source reconstruction.
