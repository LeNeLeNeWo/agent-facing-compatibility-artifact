# Input Format

## baseline_trajectory.json

```json
{
  "task_id": "airline_demo_001",
  "agent": "demo-agent",
  "seed": 0,
  "success": true,
  "steps": [
    {
      "step": 1,
      "tool": "search_flights",
      "arguments": {"origin": "JFK", "destination": "SEA"},
      "observation": {"flight_ids": ["HAT136"]}
    }
  ]
}
```

Required fields:

- `task_id`: stable task identifier.
- `success`: whether the baseline task succeeded.
- `steps`: tool calls in execution order.
- `tool`: tool name for each step.

Arguments and observations may contain nested JSON values. AFC-Gate extracts
called tools, field paths, call positions, and simple semantic hints.

## api_change_spec.json

```json
{
  "change_id": "airline_cert_card_policy_2026",
  "changed_tool": "book_reservation",
  "change_type": "C4_business_rule_drift",
  "schema_changed": false,
  "typed_client_compatible": true,
  "semantic_rule": {
    "name": "certificate_card_mix_policy",
    "before": "certificate and card payments can be mixed",
    "after": "certificate and card payments cannot be mixed unless approval_code is provided"
  },
  "observability": {
    "level": "O0_silent",
    "visible_error": false,
    "migration_note": null,
    "structured_diagnostic": null
  }
}
```

Required fields:

- `change_id`: stable change identifier.
- `changed_tool`: tool affected by the change.
- `schema_changed`: whether the visible schema changed.
- `typed_client_compatible`: whether generated clients remain callable.
- `semantic_rule`: human-readable rule before and after.
- `observability.level`: one of O0_silent through O4_migration_note.

## replay_result.json

Mock replay output contains:

- `baseline_success`
- `mutation_success`
- `hidden_violation`
- `visible_error`
- `recovery_channel`
- `failure_mode`

The public demo uses deterministic mock replay only. Real paired replay systems
should store model, task, seed, tool calls, and semantic oracle results in their
own artifact format.
