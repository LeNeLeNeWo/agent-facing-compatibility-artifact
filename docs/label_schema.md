# Label Schema

- `status`: execution status. Offline analyses count `ok` rows for success and
  hidden-violation rates; provider errors, timeouts, and failed infrastructure
  rows are not agent failures.
- `mutation_success` / `reward`: task success under the mutated condition.
- `hidden_business_rule_violation`: deterministic oracle signal for semantic
  violations not visible during the interaction.
- `observability_level`: O0 silent, visible error, structured policy error,
  migration note, or rule-visible upper-bound condition.
- `mutation_class`: taxonomy class A-D, with C-class semantic changes split
  into C1-C4 subclasses.
