"""Agent-facing compatibility classification rules."""

from __future__ import annotations

from typing import Any

from afc_gate.exposure import change_is_execution_exposed, semantic_rule_relevant
from afc_gate.observability import has_visible_recovery_signal, normalize_level
from afc_gate.schemas import APIChangeSpec, Classification


def classify(change_spec: APIChangeSpec | dict[str, Any], exposure: dict[str, Any]) -> dict[str, Any]:
    """Classify an API change for agent-facing compatibility risk."""
    change = _as_change_dict(change_spec)
    obs_level = normalize_level((change.get("observability") or {}).get("level"))
    schema_compatible = not bool(change.get("schema_changed"))
    typed_compatible = bool(change.get("typed_client_compatible", True))
    exposed = change_is_execution_exposed(change, exposure)
    relevant = semantic_rule_relevant(change, exposure) if exposed else False

    if not schema_compatible:
        risk = "medium"
        mode = "schema_visible_compatibility_risk"
        reason = "schema changed; traditional compatibility checks should flag this change"
    elif not typed_compatible:
        risk = "medium"
        mode = "typed_client_compatibility_risk"
        reason = "typed client compatibility is not preserved"
    elif not exposed:
        risk = "low"
        mode = "not_execution_exposed"
        reason = "changed tool is not called on the baseline-successful trajectory"
    elif not relevant:
        risk = "low"
        mode = "execution_exposed_but_semantic_rule_not_matched"
        reason = "changed tool is called, but the configured semantic rule is not matched by the trajectory"
    elif not has_visible_recovery_signal(obs_level):
        risk = "high"
        mode = "potential_compliant_semantic_failure"
        reason = "schema/client surface is compatible, the change is execution-exposed, and no recovery signal is visible"
    else:
        risk = "medium"
        mode = "recoverable_semantic_change_risk"
        reason = "semantic change is execution-exposed, but visible feedback provides a recovery channel"

    result = Classification(
        schema_level_compatible=schema_compatible,
        typed_client_compatible=typed_compatible,
        execution_exposed=exposed,
        semantic_rule_relevant=relevant,
        semantic_observability=obs_level,
        risk_label=risk,
        failure_mode=mode,
        reason=reason,
    )
    return result.model_dump()


def _as_change_dict(value: APIChangeSpec | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, APIChangeSpec):
        return value.model_dump()
    return APIChangeSpec.model_validate(value).model_dump()
