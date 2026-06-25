"""Baseline trajectory exposure analysis."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from afc_gate.schemas import BaselineTrajectory, Exposure


def compute_exposure(trajectory: BaselineTrajectory | dict[str, Any]) -> dict[str, Any]:
    """Extract tool, field, and semantic exposure from a baseline trajectory.

    The logic mirrors the research prototype's trajectory extractor, but uses a
    public JSON format and avoids experiment-specific artifacts.
    """
    traj = _as_trajectory(trajectory)
    tools: list[str] = []
    counts: Counter[str] = Counter()
    positions: dict[str, list[int]] = defaultdict(list)
    fields: set[str] = set()
    hints: set[str] = set()

    for index, step in enumerate(traj.steps, start=1):
        tool = step.tool
        if tool not in tools:
            tools.append(tool)
        counts[tool] += 1
        positions[tool].append(step.step or index)
        _collect_fields(step.arguments, fields)
        _collect_fields(step.observation, fields)
        hints.update(_semantic_hints(step.arguments))
        hints.update(_semantic_hints(step.observation))

    exposure = Exposure(
        tools_called=tools,
        fields_used=sorted(fields),
        semantic_hints=sorted(hints),
        tool_call_counts=dict(counts),
        tool_call_positions={k: v for k, v in positions.items()},
    )
    return exposure.model_dump()


def change_is_execution_exposed(change_spec: dict[str, Any], exposure: dict[str, Any]) -> bool:
    return str(change_spec.get("changed_tool")) in set(exposure.get("tools_called", []))


def semantic_rule_relevant(change_spec: dict[str, Any], exposure: dict[str, Any]) -> bool:
    """Heuristic rule-to-trajectory relevance check for screening.

    This is intentionally transparent: it looks for rule tokens in field names
    and known semantic hints from trajectory arguments/observations.
    """
    rule = change_spec.get("semantic_rule", {}) or {}
    text = " ".join(
        str(rule.get(k, ""))
        for k in ("name", "before", "after")
        if rule.get(k) is not None
    ).lower()
    fields = " ".join(exposure.get("fields_used", [])).lower()
    hints = set(exposure.get("semantic_hints", []))

    if "certificate" in text and "card" in text:
        return {"certificate_payment", "card_payment", "mixed_payment_methods"} <= hints
    if "refund" in text:
        return "refund" in fields or "refund" in hints
    if "baggage" in text:
        return "baggage" in fields or "baggage" in hints
    if "address" in text or "postal" in text:
        return "address" in fields or "postal_code" in fields
    if "payment" in text:
        return "payment" in fields or any(h.endswith("_payment") for h in hints)
    tokens = {t for t in _tokens(text) if len(t) >= 5}
    exposed_terms = set(_tokens(fields)) | hints
    return bool(tokens & exposed_terms)


def _as_trajectory(value: BaselineTrajectory | dict[str, Any]) -> BaselineTrajectory:
    if isinstance(value, BaselineTrajectory):
        return value
    return BaselineTrajectory.model_validate(value)


def _collect_fields(value: Any, out: set[str], prefix: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.add(path)
            _collect_fields(child, out, path)
    elif isinstance(value, list):
        for child in value:
            _collect_fields(child, out, prefix)


def _semantic_hints(value: Any) -> set[str]:
    hints: set[str] = set()
    if isinstance(value, dict):
        lower_items = {str(k).lower(): v for k, v in value.items()}
        payment_methods = lower_items.get("payment_methods")
        if isinstance(payment_methods, list):
            types = {str(p.get("type", "")).lower() for p in payment_methods if isinstance(p, dict)}
            if "certificate" in types:
                hints.add("certificate_payment")
            if "card" in types:
                hints.add("card_payment")
            if len(types) > 1:
                hints.add("mixed_payment_methods")
        for key, child in lower_items.items():
            if "refund" in key:
                hints.add("refund")
            if "baggage" in key:
                hints.add("baggage")
            if "address" in key:
                hints.add("address")
            if "postal" in key:
                hints.add("postal_code")
            hints.update(_semantic_hints(child))
    elif isinstance(value, list):
        for child in value:
            hints.update(_semantic_hints(child))
    elif isinstance(value, str):
        text = value.lower()
        if text in {"certificate", "gift_certificate"}:
            hints.add("certificate_payment")
        if text in {"card", "credit_card"}:
            hints.add("card_payment")
    return hints


def _tokens(text: str) -> list[str]:
    token = []
    out = []
    for ch in text.lower():
        if ch.isalnum() or ch == "_":
            token.append(ch)
        elif token:
            out.append("".join(token))
            token = []
    if token:
        out.append("".join(token))
    return out
