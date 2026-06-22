# User Simulator Prompt Construction

## Source Path

- Project defaults: `code/schema_mutation/batch_runner.py`.
- Project runner: `code/schema_mutation/runner.py`.
- TAU-BENCH user simulator source observed in the active Python environment:
  `C:\Users\yang\AppData\Roaming\Python\Python313\site-packages\tau_bench\envs\user.py`.

## Formal Run Configuration

- User strategy: `llm`.
- User simulator model: `dashscope/qwen-flash`.
- User simulator provider: `dashscope`.
- Task instruction source: TAU-BENCH task definition selected by environment,
  split, task index, and seed/cell metadata.

## Construction Flow

1. `code/schema_mutation/batch_runner.py` sets the default TAU-BENCH user config:
   `user_strategy=llm`, `user_model=dashscope/qwen-flash`,
   `user_provider=dashscope`, and `task_split=test`.
2. `code/schema_mutation/runner.py::run` passes those values into
   `tau_bench.envs.get_env(...)`.
3. TAU-BENCH `load_user(user_strategy="llm", model=..., provider=...)` returns
   `LLMUserSimulationEnv`.
4. `LLMUserSimulationEnv.reset(instruction)` initializes simulator messages:

```json
[
  {"role": "system", "content": "<build_system_prompt(instruction)>"},
  {"role": "user", "content": "Hi! How can I help you today?"}
]
```

5. The simulator calls LiteLLM completion with those messages and returns the
   assistant content as the first simulated user observation.

## Exactness

The static system prompt template is archived in
`user_simulator_prompt_template.txt`. The rendered task-specific prompt includes
the TAU-BENCH task instruction and was not persisted per cell in the current
formal runs.
