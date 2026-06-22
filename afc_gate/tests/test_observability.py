from afc_gate.observability import has_visible_recovery_signal, is_structured, normalize_level


def test_observability_aliases_and_visibility():
    assert normalize_level("C4b") == "O0_silent"
    assert normalize_level("policy_error") == "O2_policy_error"
    assert has_visible_recovery_signal("O0_silent") is False
    assert has_visible_recovery_signal("O2_policy_error") is True
    assert is_structured("O4_migration_note") is True
