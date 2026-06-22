# Agent Prompt Construction

## Source Path

- Project runner: `code/schema_mutation/runner.py`.
- TAU-BENCH agent source observed in the active Python environment:
  `C:\Users\yang\AppData\Roaming\Python\Python313\site-packages\tau_bench\agents\tool_calling_agent.py`.

## Construction Flow

1. `code/schema_mutation/runner.py::run` resolves the agent model/provider and
   patches LiteLLM routing for OpenAI-compatible provider endpoints.
2. `tau_bench.envs.get_env(...)` creates the TAU-BENCH retail or airline
   environment with the configured user simulator.
3. The runner optionally mutates `isolated_env.tools_info` before the agent is
   created.
4. `ToolCallingAgent` receives the final `tools_info`, `isolated_env.wiki`, the
   agent model string, and `temperature=0.0`.
5. `ToolCallingAgent.solve(...)` initializes messages as:

```json
[
  {"role": "system", "content": "<isolated_env.wiki>"},
  {"role": "user", "content": "<initial observation from env.reset(task_index=...)>"}
]
```

6. Each agent turn calls LiteLLM `completion(...)` with the current messages and
   `tools=<tools_info>`.
7. Tool calls are executed through `env.step(action)`. Tool observations are
   appended as `role=tool` messages. Final agent responses are appended as
   assistant messages followed by the next user-simulator observation.

## Observability Effects

- O0-O3 keep the tool schema and description schema-invisible for C4 semantic
  drift.
- O4 appends a migration note to the target tool description before the agent
  acts.
- O1-O3 and O4 runtime errors are emitted by the environment step wrapper, not
  by changing the agent system prompt.

## Exactness

The static message skeleton above is exact for the installed TAU-BENCH
`ToolCallingAgent`. Fully rendered per-cell messages were not emitted as
standalone artifacts in the current formal runs.
