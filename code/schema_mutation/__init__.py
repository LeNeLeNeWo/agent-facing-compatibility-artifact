"""Schema mutation testing for LLM agents.

This package implements the experimental framework for the project:
"Beyond Backward Compatibility: Testing Agent-Facing Compatibility of
Evolving Tool APIs."

Modules:
    mutator     : 14 v2 mutations (4 cls × ~14 sub-cls + 5-attribute matrix)
                  + 10 legacy v1 mutations (M01-M10) for backward compat
    runner      : Orchestrator that integrates with hal-harness / τ-bench
    metrics     : 4 core metrics for the pilot (success_drop, odds_ratio,
                  recovery_rate, mitigation_lift)

V2 Taxonomy (recommended):
    A1-A3: Identifier / representation-preserving (HAL-aligned surface baseline)
    B1-B4: Schema-contract changes (B4 = output schema, NEW)
    C1-C4: Semantic-contract changes (HERO region: traditional-compatible
                                      AND agent-silent AND semantics-changing)
    D1-D4: Protocol / operational changes

See:
    papers/01-SCHEMA-EVOLUTION-PROPOSAL.md
    papers/02-PILOT-DESIGN.md
"""

from .mutator import (
    apply_mutation,
    Mutation,
    MUTATION_TYPES,
    MUTATION_TYPES_V2,
    ATTRIBUTE_MATRIX,
    HERO_REGION,
    get_attributes,
    is_hero_region,
)

__all__ = [
    "apply_mutation",
    "Mutation",
    "MUTATION_TYPES",
    "MUTATION_TYPES_V2",
    "ATTRIBUTE_MATRIX",
    "HERO_REGION",
    "get_attributes",
    "is_hero_region",
]
