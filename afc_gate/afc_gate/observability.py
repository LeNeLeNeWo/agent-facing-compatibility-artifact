"""Semantic observability helpers derived from the paper prototype."""

from __future__ import annotations

OBSERVABILITY_LEVELS = [
    "O0_silent",
    "O1_generic_error",
    "O2_policy_error",
    "O3_structured_policy_error",
    "O4_migration_note",
]

ALIASES = {
    "silent": "O0_silent",
    "C4b": "O0_silent",
    "generic_error": "O1_generic_error",
    "O1": "O1_generic_error",
    "policy_error": "O2_policy_error",
    "visible": "O2_policy_error",
    "C4a": "O2_policy_error",
    "structured_policy_error": "O3_structured_policy_error",
    "O3": "O3_structured_policy_error",
    "migration_note": "O4_migration_note",
    "O4": "O4_migration_note",
}


def normalize_level(value: str | None) -> str:
    """Return a canonical O0-O4 observability level."""
    raw = (value or "O0_silent").strip()
    if raw in OBSERVABILITY_LEVELS:
        return raw
    if raw in ALIASES:
        return ALIASES[raw]
    raise ValueError(f"unknown observability level: {value!r}")


def has_visible_recovery_signal(level: str | None) -> bool:
    return normalize_level(level) != "O0_silent"


def is_structured(level: str | None) -> bool:
    return normalize_level(level) in {
        "O3_structured_policy_error",
        "O4_migration_note",
    }
