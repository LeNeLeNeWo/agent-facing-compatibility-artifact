"""Deterministic mock replay for public demos.

This module does not call LLMs or external APIs. It models the expected outcome
of a paired replay from exposure, semantic relevance, and observability metadata.
"""

from __future__ import annotations

from typing import Any

from afc_gate.compatibility import classify
from afc_gate.exposure import compute_exposure
from afc_gate.observability import has_visible_recovery_signal, normalize_level
from afc_gate.schemas import APIChangeSpec, BaselineTrajectory, MockReplayResult


def mock_replay(
    trajectory: BaselineTrajectory | dict[str, Any],
    change_spec: APIChangeSpec | dict[str, Any],
) -> dict[str, Any]:
    """Run a deterministic, no-API replay simulation for toy examples."""
    traj = BaselineTrajectory.model_validate(trajectory)
    change = APIChangeSpec.model_validate(change_spec).model_dump()
    exposure = compute_exposure(traj)
    cls = classify(change, exposure)
    level = normalize_level(change["observability"]["level"])
    exposed_and_relevant = cls["execution_exposed"] and cls["semantic_rule_relevant"]
    visible = exposed_and_relevant and has_visible_recovery_signal(level)

    if not exposed_and_relevant:
        success = traj.success
        hidden = False
        mode = "not_agent_facing_for_this_trajectory"
    elif level == "O0_silent":
        success = False
        hidden = True
        mode = "potential_compliant_semantic_failure"
    else:
        success = True
        hidden = False
        mode = "recovered_via_visible_semantic_feedback"

    result = MockReplayResult(
        task_id=traj.task_id,
        change_id=change["change_id"],
        baseline_success=traj.success,
        mutation_success=success,
        hidden_violation=hidden,
        visible_error=visible,
        recovery_channel=visible,
        execution_exposed=cls["execution_exposed"],
        semantic_rule_relevant=cls["semantic_rule_relevant"],
        failure_mode=mode,
        observability_level=level,
    )
    return result.model_dump()
