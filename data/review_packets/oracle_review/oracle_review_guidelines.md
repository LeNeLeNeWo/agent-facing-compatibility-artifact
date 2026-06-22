# Phase 10B Oracle Review Guidelines

Reviewers should inspect the trace pointer, tool-call summary, final-state summary, and evolved rule. The goal is to validate whether the deterministic oracle label matches the intended semantic rule.

## Review Questions

- Does `oracle_flag` agree with the evolved rule?
- Is a positive O0 case truly a compliant semantic failure: syntactically valid call, unchanged schema/call surface, no visible policy signal, but final state violates the evolved rule?
- Should the baseline unmutated case avoid triggering the oracle?
- Is an O0 negative truly a non-violation?
- Is a recovered case truly a recovery rather than an unrelated success?
- If the task, wrapper behavior, or final state is ambiguous, mark the sample `suspicious`.

## Labels

- `human_oracle_correct`: yes / no / unclear / suspicious.
- `human_failure_type`: compliant_semantic_failure / visible_recovery / non_violation / infrastructure / ambiguous / other.
- `human_confidence`: high / medium / low.

Do not calculate inter-annotator agreement until two independent human label sets exist.
