from afc_gate.exposure import compute_exposure


def test_exposure_extracts_called_tools_and_fields():
    trajectory = {
        "task_id": "airline_demo_001",
        "success": True,
        "steps": [
            {
                "tool": "search_flights",
                "arguments": {"origin": "JFK", "destination": "SEA"},
                "observation": {"flight_ids": ["HAT136"]},
            },
            {
                "tool": "book_reservation",
                "arguments": {
                    "payment_methods": [
                        {"type": "certificate", "amount": 250},
                        {"type": "card", "amount": 5},
                    ]
                },
                "observation": {"status": "booked"},
            },
        ],
    }

    exposure = compute_exposure(trajectory)

    assert exposure["tools_called"] == ["search_flights", "book_reservation"]
    assert "origin" in exposure["fields_used"]
    assert "payment_methods.type" in exposure["fields_used"]
    assert "mixed_payment_methods" in exposure["semantic_hints"]
