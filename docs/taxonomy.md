# Mutation Taxonomy

- A: schema-visible surface changes such as parameter or type changes.
- B: protocol/interface changes that alter call mechanics.
- C: schema-invisible semantic changes.
  - C1: unit, scale, or validation boundary drift.
  - C2: currency, locale, or interpretation drift.
  - C3: default-behavior drift.
  - C4: business-rule or policy drift.
- D: other non-local or mixed changes.

The paper focuses on compliant semantic failures: cases where the tool call may
remain schema-compliant while the external semantic contract has changed.
