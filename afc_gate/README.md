# AFC-Gate

Agent-Facing Compatibility Gate for Evolving Tool APIs.

AFC-Gate is a lightweight toolkit for testing whether evolving tool APIs remain
compatible with LLM agents by combining baseline trajectory exposure analysis,
semantic-change specifications, targeted replay planning, and compatibility
reporting.

## Why Schema Compatibility Is Not Enough

Traditional API compatibility checks ask whether a schema changed, whether a
typed client can still call the endpoint, and whether argument formats remain
legal. Tool-using agents also depend on task semantics, business rules, tool
descriptions, execution paths, runtime feedback, and recovery signals. An API
can remain syntactically callable while silently changing a rule that an agent
relies on.

## Key Concepts

- Agent-facing compatibility: an evolved API remains compatible with the agent
  behavior that previously solved a task.
- Compliant semantic failure: the endpoint, schema, and call signature remain
  compatible, but task success fails because a silent semantic rule changed.
- Execution exposure: the changed tool or rule is on the agent's baseline
  successful path.
- Semantic observability: whether the evolved rule is silent or visible through
  errors, structured diagnostics, or migration notes.
- Paired replay: rerunning a baseline-successful task against an evolved API to
  test whether the agent-facing behavior still succeeds.

## Quick Start

```bash
cd afc_gate
pip install -e .
afc-gate demo
```

The demo writes:

```text
runs/afc_gate_demo/exposure.json
runs/afc_gate_demo/replay_plan.json
runs/afc_gate_demo/mock_replay_results.json
runs/afc_gate_demo/report.md
```

The demo is deterministic and does not call external APIs.

## CLI

```bash
afc-gate analyze \
  --trajectories examples/toy_airline/baseline_trajectory.json \
  --changes examples/toy_airline/api_change_spec.json \
  --out runs/afc_gate_demo/report.md

afc-gate plan \
  --trajectories examples/toy_airline/baseline_trajectory.json \
  --changes examples/toy_airline/api_change_spec.json \
  --out runs/afc_gate_demo/replay_plan.json

afc-gate mock-replay \
  --trajectories examples/toy_airline/baseline_trajectory.json \
  --changes examples/toy_airline/api_change_spec.json \
  --out runs/afc_gate_demo/mock_replay_results.json
```

## Input Formats

A baseline trajectory records a successful agent path: task id, agent name,
seed, success flag, and a list of tool calls with arguments and observations.

An API change spec records the changed tool, whether the schema changed,
whether typed clients remain compatible, the semantic rule before and after,
and the observability level.

See [docs/input_format.md](docs/input_format.md) for details.

## CI/CD Integration

AFC-Gate can be used as a lightweight pre-merge screening step for tool schema,
policy, or business-rule changes. The default workflow is:

1. Save representative baseline-successful trajectories.
2. Write semantic-change specs for candidate API changes.
3. Run `afc-gate analyze`.
4. Review high risk task/change pairs and add paired replay tests.

See [docs/ci_cd_integration.md](docs/ci_cd_integration.md).

## What AFC-Gate Is Not

- Not a production certification system.
- Not an LLM judge.
- Not a replacement for schema checks.
- Not a full API monitoring platform.
- Not proof that all production traffic is safe.

## Relationship to the Paper

The toolkit packages the paper's engineering framework as a public prototype:
agent-facing compatibility, execution exposure, semantic observability, targeted
paired replay planning, and compatibility reporting. It is not a replacement for
the empirical study or its frozen experimental artifacts.

See [docs/paper_mapping.md](docs/paper_mapping.md).

## Artifact Boundary

This directory contains public toy examples only. Real experiment artifacts,
provider logs, and full trajectories should be released separately after
anonymization and review. Do not include provider tokens, private endpoints, raw
provider logs, or unredacted user data in this package.
