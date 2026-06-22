"""Decision policies for AFC-Gate.

This module contains deterministic rules only. It does not look at evaluation
labels unless a caller explicitly passes replay evidence produced by a gate run.
"""

from __future__ import annotations

from dataclasses import dataclass


GATE_METHODS = [
    "SchemaCheckerOnly",
    "RandomReplayGate",
    "UsedToolReplayGate",
    "IntentAlignedReplayGate",
    "AFCGate",
    "ExhaustiveReplayOracle",
]

POSITIVE_DECISIONS = {
    "warn",
    "block",
    "needs_migration_note",
    "needs_structured_policy_error",
}


@dataclass(frozen=True)
class StaticCompatResult:
    schema_checker_pass: bool
    typed_client_checker_pass: bool
    reasons: tuple[str, ...] = ()


def decision_is_positive(decision: str) -> bool:
    return decision in POSITIVE_DECISIONS


def classify_static_compat(mutation: str | None) -> StaticCompatResult:
    """Approximate schema/client compatibility for mutation classes.

    This is a baseline pre-deployment checker. It intentionally treats C1-C4 as
    schema/client compatible because those mutations are semantic drifts whose
    risky content is not represented in the JSON-schema signature.
    """
    if not mutation:
        return StaticCompatResult(True, True, ())

    schema_visible = mutation.startswith(("A1_", "A2_", "B1_", "B2_", "B3_", "B4_"))
    typed_break = mutation.startswith(("A1_", "A2_", "B1_", "B2_", "B3_"))
    if schema_visible or typed_break:
        reasons = []
        if schema_visible:
            reasons.append("schema_signature_or_contract_changed")
        if typed_break:
            reasons.append("generated_client_may_break")
        return StaticCompatResult(
            schema_checker_pass=not schema_visible,
            typed_client_checker_pass=not typed_break,
            reasons=tuple(reasons),
        )
    return StaticCompatResult(True, True, ())


def exposure_level(target_policy: str | None, mutation_tool: str | None, oracle_action: str | None) -> str:
    """Return a coarse exposure level from pre-replay metadata.

    Prediction feature: baseline exposure/targeting policy only. The oracle
    action is used only when it came from gate replay evidence.
    """
    policy = str(target_policy or "random")
    if policy in {"unused_tool", "unused_intent_aligned"}:
        return "unexposed"
    if policy in {"intent_aligned", "random_intent_aligned"}:
        return "intent_aligned"
    if policy == "used_tool":
        return "used_tool"
    if mutation_tool and oracle_action and mutation_tool == oracle_action:
        return "executed_target_tool"
    if mutation_tool:
        return "candidate_tool"
    return "unknown"


def observability_signal(record: dict) -> str:
    if record.get("migration_note_visible"):
        return "migration_note"
    if record.get("structured_policy_error_visible"):
        return "structured_policy_error"
    if record.get("generic_error_visible"):
        return "generic_error"
    if record.get("visible_policy_error"):
        return "policy_error"
    mode = str(record.get("observability_level") or record.get("c4_runtime_mode") or "")
    if mode in {"O4_migration_note", "migration_note"}:
        return "migration_note"
    if mode in {"O3_structured_policy_error", "structured_policy_error"}:
        return "structured_policy_error"
    if mode in {"O1_generic_error", "generic_error"}:
        return "generic_error"
    if mode in {"O2_policy_error", "visible", "C4a", "visible_policy_violation"}:
        return "policy_error"
    return "none"


def afc_decision(
    *,
    static_result: StaticCompatResult,
    execution_exposed: bool,
    semantic_oracle_pass: bool | None,
    observability: str,
    replay_ran: bool,
) -> tuple[str, str]:
    """Main AFC-Gate policy.

    Features used before replay: static_result, exposure, observability metadata.
    Gate execution evidence: semantic_oracle_pass only if replay_ran is true.
    Evaluation labels such as final agent success are not used here.
    """
    if not static_result.schema_checker_pass or not static_result.typed_client_checker_pass:
        return "warn", "static schema/client checker reports a compatibility risk"
    if not execution_exposed:
        return "pass", "candidate change is not exposed on baseline-successful paths"
    if semantic_oracle_pass is False:
        if observability == "none":
            return "block", "schema-compatible exposed path fails semantic oracle with no visible recovery signal"
        if observability in {"generic_error", "policy_error"}:
            return (
                "needs_structured_policy_error",
                "semantic oracle fails; visible feedback exists but is not structured/actionable",
            )
        if observability == "structured_policy_error":
            return (
                "needs_migration_note",
                "semantic oracle fails after first violating call; pre-call migration metadata is recommended",
            )
        return "warn", "semantic oracle fails but migration metadata is visible"
    if replay_ran and semantic_oracle_pass is True:
        return "pass", "replayed exposed path satisfies semantic oracle"
    if observability == "none":
        return "warn", "schema-compatible semantic change is exposed but not replayed"
    return "pass", "no blocking evidence under current budget"
