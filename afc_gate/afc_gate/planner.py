"""Targeted replay planning for AFC-Gate."""

from __future__ import annotations

from typing import Any

from afc_gate.compatibility import classify
from afc_gate.exposure import compute_exposure
from afc_gate.schemas import APIChangeSpec, BaselineTrajectory, ReplayPlanItem


def plan_replay(
    trajectories: list[BaselineTrajectory | dict[str, Any]],
    change_specs: list[APIChangeSpec | dict[str, Any]],
) -> list[dict[str, Any]]:
    """Create a prioritized paired-replay plan from trajectories and changes."""
    plans: list[dict[str, Any]] = []
    changes = [APIChangeSpec.model_validate(c).model_dump() for c in change_specs]
    for raw_traj in trajectories:
        traj = BaselineTrajectory.model_validate(raw_traj)
        if not traj.success:
            continue
        exposure = compute_exposure(traj)
        for change in changes:
            cls = classify(change, exposure)
            priority = cls["risk_label"]
            if cls["failure_mode"] == "potential_compliant_semantic_failure":
                test = "paired_replay"
            elif cls["execution_exposed"]:
                test = "paired_replay_with_observability_check"
            else:
                test = "no_replay_needed_for_this_task"
            item = ReplayPlanItem(
                task_id=traj.task_id,
                change_id=change["change_id"],
                changed_tool=change["changed_tool"],
                execution_exposed=cls["execution_exposed"],
                semantic_rule_relevant=cls["semantic_rule_relevant"],
                reason=_reason(change, cls),
                priority=priority,
                recommended_test=test,
                classification=cls,
            )
            plans.append(item.model_dump())
    return sorted(plans, key=_priority_key)


def _reason(change: dict[str, Any], cls: dict[str, Any]) -> str:
    tool = change["changed_tool"]
    if cls["failure_mode"] == "potential_compliant_semantic_failure":
        return (
            f"changed tool {tool} is execution-exposed and the semantic rule is "
            "matched by the baseline trajectory without a visible recovery signal"
        )
    if cls["failure_mode"] == "not_execution_exposed":
        return f"changed tool {tool} is not called by this baseline trajectory"
    return cls["reason"]


def _priority_key(item: dict[str, Any]) -> tuple[int, str, str]:
    order = {"high": 0, "medium": 1, "low": 2}
    return (order[item["priority"]], item["task_id"], item["change_id"])
