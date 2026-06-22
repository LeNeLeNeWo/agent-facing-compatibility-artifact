# AFC-Gate Compatibility Report

## Summary
- Total baseline-successful tasks: 1
- Planned change-task checks: 1
- Execution-exposed changes: 1
- Potential compliant semantic failures: 1
- Silent semantic drifts: 1
- Recoverable visible changes: 0
- Mock hidden violations: 1
- Mock recoveries via visible feedback: 0

## High Risk Findings
- `airline_demo_001` x `airline_cert_card_policy_2026`: potential_compliant_semantic_failure. changed tool book_reservation is execution-exposed and the semantic rule is matched by the baseline trajectory without a visible recovery signal.

## Replay Plan
- `high` `paired_replay` for `airline_demo_001` / `airline_cert_card_policy_2026`: changed tool book_reservation is execution-exposed and the semantic rule is matched by the baseline trajectory without a visible recovery signal.

## Recommended Actions
- Add paired replay tests for high risk execution-exposed semantic changes.
- Add policy errors for silent business-rule drifts.
- Add structured diagnostics for recoverable but underspecified failures.
- Add migration notes for changes agents should see before making a violating call.

## Boundary
This report is produced by deterministic screening and mock replay. It is not an LLM judge and does not call external APIs.
