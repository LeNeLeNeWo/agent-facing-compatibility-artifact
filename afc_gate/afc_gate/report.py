"""Markdown reporting for AFC-Gate."""

from __future__ import annotations

from typing import Any


def generate_report(results: dict[str, Any] | list[dict[str, Any]]) -> str:
    """Generate a compact Markdown compatibility report."""
    data = _normalize_results(results)
    plans = data.get("replay_plan", [])
    replay = data.get("mock_replay_results", [])
    exposures = data.get("exposures", [])
    high = [p for p in plans if p.get("priority") == "high"]
    silent = [p for p in plans if p.get("classification", {}).get("semantic_observability") == "O0_silent"]
    visible = [p for p in plans if p.get("classification", {}).get("semantic_observability") != "O0_silent"]
    exposed = [p for p in plans if p.get("execution_exposed")]
    hidden = [r for r in replay if r.get("hidden_violation")]
    recovered = [r for r in replay if r.get("recovery_channel")]

    lines = [
        "# AFC-Gate Compatibility Report",
        "",
        "## Summary",
        f"- Total baseline-successful tasks: {len(exposures)}",
        f"- Planned change-task checks: {len(plans)}",
        f"- Execution-exposed changes: {len(exposed)}",
        f"- Potential compliant semantic failures: {len(high)}",
        f"- Silent semantic drifts: {len(silent)}",
        f"- Recoverable visible changes: {len(visible)}",
        f"- Mock hidden violations: {len(hidden)}",
        f"- Mock recoveries via visible feedback: {len(recovered)}",
        "",
        "## High Risk Findings",
    ]
    if high:
        for item in high:
            lines.append(
                f"- `{item['task_id']}` x `{item['change_id']}`: "
                f"{item['classification']['failure_mode']}. {item['reason']}."
            )
    else:
        lines.append("- No high risk task/change pairs found.")

    lines.extend(["", "## Replay Plan"])
    for item in plans:
        lines.append(
            f"- `{item['priority']}` `{item['recommended_test']}` for "
            f"`{item['task_id']}` / `{item['change_id']}`: {item['reason']}."
        )

    lines.extend(
        [
            "",
            "## Recommended Actions",
            "- Add paired replay tests for high risk execution-exposed semantic changes.",
            "- Add policy errors for silent business-rule drifts.",
            "- Add structured diagnostics for recoverable but underspecified failures.",
            "- Add migration notes for changes agents should see before making a violating call.",
            "",
            "## Boundary",
            "This report is produced by deterministic screening and mock replay. It is not an LLM judge and does not call external APIs.",
        ]
    )
    return "\n".join(lines) + "\n"


def _normalize_results(results: dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any]:
    if isinstance(results, list):
        return {"mock_replay_results": results, "replay_plan": [], "exposures": []}
    return results
