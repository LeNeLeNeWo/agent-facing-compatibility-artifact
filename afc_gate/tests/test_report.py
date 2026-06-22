from afc_gate.exposure import compute_exposure
from afc_gate.planner import plan_replay
from afc_gate.replay import mock_replay
from afc_gate.report import generate_report


def test_report_contains_potential_compliant_semantic_failure():
    trajectory = {
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
    change = {
        "change_id": "airline_cert_card_policy_2026",
        "changed_tool": "book_reservation",
        "schema_changed": False,
        "typed_client_compatible": True,
        "semantic_rule": {
            "name": "certificate_card_mix_policy",
            "after": "certificate and card payments cannot be mixed unless approval_code is provided",
        },
        "observability": {"level": "O0_silent"},
    }
    report = generate_report(
        {
            "exposures": [compute_exposure(trajectory)],
            "replay_plan": plan_replay([trajectory], [change]),
            "mock_replay_results": [mock_replay(trajectory, change)],
        }
    )

    assert "potential_compliant_semantic_failure" in report
