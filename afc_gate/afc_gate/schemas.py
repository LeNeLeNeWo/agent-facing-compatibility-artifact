"""Public input and output schemas for AFC-Gate."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ObservabilityLevel = Literal[
    "O0_silent",
    "O1_generic_error",
    "O2_policy_error",
    "O3_structured_policy_error",
    "O4_migration_note",
]


class TrajectoryStep(BaseModel):
    step: int | None = None
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    observation: dict[str, Any] = Field(default_factory=dict)


class BaselineTrajectory(BaseModel):
    task_id: str
    agent: str | None = None
    seed: int | None = None
    success: bool = True
    steps: list[TrajectoryStep] = Field(default_factory=list)


class SemanticRule(BaseModel):
    name: str
    before: str | None = None
    after: str


class ObservabilitySpec(BaseModel):
    level: ObservabilityLevel = "O0_silent"
    visible_error: bool = False
    migration_note: str | None = None
    structured_diagnostic: dict[str, Any] | None = None


class APIChangeSpec(BaseModel):
    change_id: str
    changed_tool: str
    change_type: str = "C4_business_rule_drift"
    schema_changed: bool = False
    typed_client_compatible: bool = True
    semantic_rule: SemanticRule
    observability: ObservabilitySpec = Field(default_factory=ObservabilitySpec)


class Exposure(BaseModel):
    tools_called: list[str] = Field(default_factory=list)
    fields_used: list[str] = Field(default_factory=list)
    semantic_hints: list[str] = Field(default_factory=list)
    tool_call_counts: dict[str, int] = Field(default_factory=dict)
    tool_call_positions: dict[str, list[int]] = Field(default_factory=dict)


class Classification(BaseModel):
    schema_level_compatible: bool
    typed_client_compatible: bool
    execution_exposed: bool
    semantic_rule_relevant: bool
    semantic_observability: ObservabilityLevel
    risk_label: Literal["low", "medium", "high"]
    failure_mode: str
    reason: str


class ReplayPlanItem(BaseModel):
    task_id: str
    change_id: str
    changed_tool: str
    execution_exposed: bool
    semantic_rule_relevant: bool
    reason: str
    priority: Literal["low", "medium", "high"]
    recommended_test: str
    classification: Classification


class MockReplayResult(BaseModel):
    task_id: str
    change_id: str
    baseline_success: bool
    mutation_success: bool
    hidden_violation: bool
    visible_error: bool
    recovery_channel: bool
    execution_exposed: bool
    semantic_rule_relevant: bool
    failure_mode: str
    observability_level: ObservabilityLevel
