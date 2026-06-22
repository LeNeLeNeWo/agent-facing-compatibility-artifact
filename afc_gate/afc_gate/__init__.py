"""AFC-Gate: Agent-Facing Compatibility Gate for evolving tool APIs."""

from afc_gate.compatibility import classify
from afc_gate.exposure import compute_exposure
from afc_gate.planner import plan_replay
from afc_gate.replay import mock_replay
from afc_gate.report import generate_report

__all__ = [
    "classify",
    "compute_exposure",
    "generate_report",
    "mock_replay",
    "plan_replay",
]

__version__ = "0.1.0"
