from afc_gate.compatibility import classify
from afc_gate.exposure import compute_exposure
from afc_gate.planner import plan_replay


TRAJECTORY = {
    "task_id": "airline_demo_001",
    "success": True,
    "steps": [
        {
            "tool": "book_reservation",
            "arguments": {
                "payment_methods": [
                    {"type": "certificate", "amount": 250},
                    {"type": "card", "amount": 5},
                ]
            },
            "observation": {"status": "booked"},
        }
    ],
}

SILENT_CHANGE = {
    "change_id": "airline_cert_card_policy_2026",
    "changed_tool": "book_reservation",
    "schema_changed": False,
    "typed_client_compatible": True,
    "semantic_rule": {
        "name": "certificate_card_mix_policy",
        "before": "certificate and card payments can be mixed",
        "after": "certificate and card payments cannot be mixed unless approval_code is provided",
    },
    "observability": {"level": "O0_silent"},
}


def test_schema_compatible_silent_exposed_change_is_high_risk():
    exposure = compute_exposure(TRAJECTORY)

    result = classify(SILENT_CHANGE, exposure)

    assert result["risk_label"] == "high"
    assert result["failure_mode"] == "potential_compliant_semantic_failure"
    assert result["execution_exposed"] is True


def test_unused_tool_change_is_low_task_specific_risk():
    exposure = compute_exposure(TRAJECTORY)
    change = dict(SILENT_CHANGE, changed_tool="cancel_reservation")

    result = classify(change, exposure)

    assert result["risk_label"] == "low"
    assert result["failure_mode"] == "not_execution_exposed"


def test_o3_change_is_recoverable_semantic_change_risk():
    exposure = compute_exposure(TRAJECTORY)
    change = dict(SILENT_CHANGE)
    change["observability"] = {"level": "O3_structured_policy_error"}

    result = classify(change, exposure)

    assert result["risk_label"] == "medium"
    assert result["failure_mode"] == "recoverable_semantic_change_risk"


def test_plan_replay_prioritizes_high_risk_pair():
    plan = plan_replay([TRAJECTORY], [SILENT_CHANGE])

    assert plan[0]["priority"] == "high"
    assert plan[0]["recommended_test"] == "paired_replay"
