# Concepts

## Agent-Facing Compatibility

An evolved tool API is agent-facing compatible when an agent that previously
solved a task can still solve that task after the API changes. This is stricter
than schema compatibility because it includes task semantics and runtime
feedback.

## Agent-Facing Regression

An agent-facing regression occurs when a baseline-successful trajectory no
longer produces a successful task outcome under the evolved API.

## Compliant Semantic Failure

A compliant semantic failure is a high risk special case: the call remains
valid, the schema and typed client remain compatible, and the agent receives no
visible error, yet the final task state violates the evolved business rule.

## Execution Exposure

Execution exposure asks whether the changed tool or rule lies on the agent's
baseline successful path. A change to an unused tool can still matter globally,
but it is lower risk for that specific task trajectory.

## Semantic Observability

AFC-Gate uses five observability levels:

- O0_silent: the rule changes without visible feedback.
- O1_generic_error: the agent sees a generic failure.
- O2_policy_error: the agent sees a policy error.
- O3_structured_policy_error: the agent sees structured diagnostics.
- O4_migration_note: the agent receives pre-call migration metadata.

The key engineering distinction is whether the agent has a recovery channel.
