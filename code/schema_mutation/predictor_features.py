"""Feature definitions for deconfounded agent-breakage prediction.

Label/evaluation fields are explicitly separated from legal predictor
features. Feature families are validated before evaluation so accidental
leakage is caught early.
"""

from __future__ import annotations

from typing import Any


LEAKAGE_FIELDS = {
    "mutation_success",
    "final_reward",
    "agent_breaking",
    "failure_mode",
    "oracle_rule_violation",
    "hidden_business_rule_violation",
    "recovery_success",
    "semantic_oracle_pass",
    "gate_decision",
    "gate_reason",
}


FEATURE_FAMILIES: dict[str, list[str]] = {
    "majority": [],
    "schema_diff_only": [
        "schema_visible",
        "endpoint_changed",
        "param_rename",
        "type_changed",
        "requiredness_changed",
        "enum_changed",
        "output_shape_changed",
        "schema_client_compatible",
    ],
    "semantic_only": [
        "mutation_class",
        "semantic_change",
        "unit_scale",
        "currency_locale",
        "default_behavior",
        "business_rule",
        "protocol_change",
        "target_policy_type",
    ],
    "exposure_only": [
        "target_tool_called",
        "target_param_used",
        "target_response_observed",
        "intent_aligned",
        "field_state_exposed",
        "tool_call_position",
        "tool_call_frequency",
    ],
    "observability_only": [
        "visible_error",
        "generic_error",
        "structured_error",
        "migration_note",
        "silent",
        "observability_level",
    ],
    "trajectory_only": [
        "baseline_num_tool_calls",
        "baseline_num_retries",
        "baseline_trajectory_length",
        "tool_call_position",
    ],
    "exposure+semantic": [
        "target_tool_called",
        "target_param_used",
        "target_response_observed",
        "intent_aligned",
        "field_state_exposed",
        "tool_call_position",
        "tool_call_frequency",
        "mutation_class",
        "semantic_change",
        "unit_scale",
        "currency_locale",
        "default_behavior",
        "business_rule",
        "protocol_change",
        "target_policy_type",
    ],
    "exposure+semantic+observability": [
        "target_tool_called",
        "target_param_used",
        "target_response_observed",
        "intent_aligned",
        "field_state_exposed",
        "tool_call_position",
        "tool_call_frequency",
        "mutation_class",
        "semantic_change",
        "unit_scale",
        "currency_locale",
        "default_behavior",
        "business_rule",
        "protocol_change",
        "target_policy_type",
        "visible_error",
        "generic_error",
        "structured_error",
        "migration_note",
        "silent",
        "observability_level",
    ],
    "all_features": [
        "schema_visible",
        "endpoint_changed",
        "param_rename",
        "type_changed",
        "requiredness_changed",
        "enum_changed",
        "output_shape_changed",
        "schema_client_compatible",
        "mutation_class",
        "semantic_change",
        "unit_scale",
        "currency_locale",
        "default_behavior",
        "business_rule",
        "protocol_change",
        "target_policy_type",
        "target_tool_called",
        "target_param_used",
        "target_response_observed",
        "intent_aligned",
        "field_state_exposed",
        "reward_critical_prior",
        "tool_call_position",
        "tool_call_frequency",
        "visible_error",
        "generic_error",
        "structured_error",
        "migration_note",
        "silent",
        "observability_level",
        "baseline_num_tool_calls",
        "baseline_num_retries",
        "baseline_trajectory_length",
    ],
}


def validate_feature_family(name: str, features: list[str]) -> list[str]:
    leaked = [f for f in features if f in LEAKAGE_FIELDS]
    if leaked:
        raise ValueError(f"feature family {name!r} contains leakage fields: {leaked}")
    return features


def legal_feature_families() -> dict[str, list[str]]:
    return {name: validate_feature_family(name, list(features)) for name, features in FEATURE_FAMILIES.items()}


def feature_value(row: dict[str, Any], feature: str) -> Any:
    if feature in LEAKAGE_FIELDS:
        raise ValueError(f"leakage feature requested: {feature}")
    return row.get(feature)
