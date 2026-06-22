"""C4 observability-gradient definitions.

The gradient keeps the underlying semantic business-rule drift fixed and varies
only what the agent can observe before or after a violating tool call.
"""

from __future__ import annotations

import json
from typing import Any


OBSERVABILITY_LEVELS = [
    "O0_silent",
    "O1_generic_error",
    "O2_policy_error",
    "O3_structured_policy_error",
    "O4_migration_note",
]

OBSERVABILITY_ALIASES = {
    "": None,
    "none": None,
    "null": None,
    "silent": "O0_silent",
    "C4b": "O0_silent",
    "silent_business_rule_drift": "O0_silent",
    "generic_error": "O1_generic_error",
    "O1": "O1_generic_error",
    "visible": "O2_policy_error",
    "C4a": "O2_policy_error",
    "visible_policy_violation": "O2_policy_error",
    "policy_error": "O2_policy_error",
    "O2": "O2_policy_error",
    "structured_policy_error": "O3_structured_policy_error",
    "O3": "O3_structured_policy_error",
    "migration_note": "O4_migration_note",
    "O4": "O4_migration_note",
}

LEVEL_TO_RUNTIME_MODE = {
    "O0_silent": "silent",
    "O1_generic_error": "generic_error",
    "O2_policy_error": "visible",
    "O3_structured_policy_error": "structured_policy_error",
    "O4_migration_note": "migration_note",
}


def normalize_observability_level(
    observability_level: str | None = None,
    c4_runtime_mode: str | None = None,
) -> str:
    """Return a canonical O0-O4 level.

    Older experiments only set ``c4_runtime_mode``. We map those values here so
    historical C4a/C4b command lines remain valid.
    """
    raw = str(observability_level or "").strip()
    if raw in OBSERVABILITY_LEVELS:
        return raw
    mapped = OBSERVABILITY_ALIASES.get(raw)
    if mapped:
        return mapped

    mode = str(c4_runtime_mode or "").strip()
    if mode in OBSERVABILITY_LEVELS:
        return mode
    mapped = OBSERVABILITY_ALIASES.get(mode)
    if mapped:
        return mapped

    raise ValueError(
        f"unknown C4 observability level/mode: "
        f"observability_level={observability_level!r}, c4_runtime_mode={c4_runtime_mode!r}"
    )


def runtime_mode_for_level(level: str) -> str:
    return LEVEL_TO_RUNTIME_MODE[normalize_observability_level(level)]


def migration_note(tool_name: str | None, drift: str) -> str:
    tool = tool_name or "the target tool"
    return (
        f"Migration note: The {tool} API has updated its business policy. "
        f"{drift}"
    )


def generic_error_message() -> str:
    return "Operation failed. Request cannot be completed."


def policy_error_message(drift: str) -> str:
    return (
        "Policy violation: this request does not satisfy the updated API "
        f"business policy. {drift}"
    )


def structured_policy_error(
    *,
    intent: str | None,
    action_name: str,
    drift: str,
) -> dict[str, Any]:
    policy = f"{intent or 'business'}_rule_drift"
    return {
        "error": "policy_violation",
        "policy": policy,
        "offending_action": action_name,
        "offending_field": _offending_field(intent, action_name),
        "message": drift,
        "suggested_action": _suggested_action(intent),
    }


def structured_policy_error_text(*, intent: str | None, action_name: str, drift: str) -> str:
    return json.dumps(
        structured_policy_error(intent=intent, action_name=action_name, drift=drift),
        ensure_ascii=False,
    )


def _offending_field(intent: str | None, action_name: str) -> str:
    by_intent = {
        "book_flight": "payment_methods",
        "change_flight": "fare_class",
        "baggage": "passenger_identity",
        "passenger": "birthdate",
        "payment": "payment_method",
        "return": "refund_method",
        "cancel": "confirmation",
        "address": "postal_code",
        "modify_order": "item_attributes",
        "exchange": "replacement_item",
    }
    return by_intent.get(intent or "", action_name or "request")


def _suggested_action(intent: str | None) -> str:
    by_intent = {
        "book_flight": "Use a single payment method or request explicit approval.",
        "change_flight": "Check fare-class eligibility before updating the reservation.",
        "baggage": "Verify passenger identity in the same request before changing baggage.",
        "passenger": "Verify birthdate in the same request before updating passenger details.",
        "payment": "Use the original payment method or obtain explicit approval.",
        "return": "Refund to the original payment method.",
        "cancel": "Collect explicit confirmation and use the original payment instrument.",
        "address": "Re-verify the postal code before updating the address.",
        "modify_order": "Limit pending item changes to allowed attributes.",
        "exchange": "Choose a replacement matching both product type and brand.",
    }
    return by_intent.get(
        intent or "",
        "Review the updated business rule and retry with a compliant request.",
    )


def level_flags(level: str, violated: bool) -> dict[str, bool]:
    level = normalize_observability_level(level)
    visible = violated and level in {
        "O1_generic_error",
        "O2_policy_error",
        "O3_structured_policy_error",
        "O4_migration_note",
    }
    return {
        "generic_error_visible": violated and level == "O1_generic_error",
        "visible_policy_error": visible,
        "structured_policy_error_visible": violated
        and level in {"O3_structured_policy_error", "O4_migration_note"},
        "migration_note_visible": level == "O4_migration_note",
        "hidden_business_rule_violation": violated and level == "O0_silent",
    }


def observability_order(level: str | None) -> int:
    level = normalize_observability_level(level or "O0_silent")
    return OBSERVABILITY_LEVELS.index(level)


def c4_mode_matches(record: dict[str, Any], mode: str) -> bool:
    """Match old Day-16 mode labels against either old or new fields."""
    wanted = normalize_observability_level(None, mode)
    level = record.get("observability_level")
    if level:
        try:
            return normalize_observability_level(str(level)) == wanted
        except ValueError:
            return False
    return normalize_observability_level(None, str(record.get("c4_runtime_mode") or "")) == wanted
