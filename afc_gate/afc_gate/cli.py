"""Command line interface for AFC-Gate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from afc_gate.exposure import compute_exposure
from afc_gate.io_utils import as_list, read_json, write_json, write_text
from afc_gate.planner import plan_replay
from afc_gate.replay import mock_replay
from afc_gate.report import generate_report
from afc_gate.schemas import APIChangeSpec, BaselineTrajectory


@click.group()
def main() -> None:
    """AFC-Gate: agent-facing compatibility screening for evolving tool APIs."""


@main.command()
@click.option("--trajectories", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--changes", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--out", required=True, type=click.Path(path_type=Path))
def analyze(trajectories: Path, changes: Path, out: Path) -> None:
    """Run exposure analysis, replay planning, mock replay, and report generation."""
    bundle = _run_pipeline(trajectories, changes)
    write_text(out, generate_report(bundle))
    click.echo(f"report written: {out}")


@main.command("plan")
@click.option("--trajectories", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--changes", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--out", required=True, type=click.Path(path_type=Path))
def plan_cmd(trajectories: Path, changes: Path, out: Path) -> None:
    """Generate a replay plan without running mock replay."""
    trajs = _load_trajectories(trajectories)
    specs = _load_changes(changes)
    write_json(out, plan_replay(trajs, specs))
    click.echo(f"replay plan written: {out}")


@main.command("mock-replay")
@click.option("--trajectories", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--changes", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--out", required=True, type=click.Path(path_type=Path))
def mock_replay_cmd(trajectories: Path, changes: Path, out: Path) -> None:
    """Run deterministic local mock replay for toy examples."""
    trajs = _load_trajectories(trajectories)
    specs = _load_changes(changes)
    write_json(out, _mock_replay_all(trajs, specs))
    click.echo(f"mock replay results written: {out}")


@main.command("report")
@click.option("--results", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--out", required=True, type=click.Path(path_type=Path))
def report_cmd(results: Path, out: Path) -> None:
    """Render a Markdown report from a JSON result bundle."""
    write_text(out, generate_report(read_json(results)))
    click.echo(f"report written: {out}")


@main.command()
@click.option("--out-dir", default=None, type=click.Path(path_type=Path))
def demo(out_dir: Path | None) -> None:
    """Run the toy airline demo without external API calls."""
    root = _project_root()
    demo_out = out_dir or _default_demo_out()
    traj_path = root / "examples" / "toy_airline" / "baseline_trajectory.json"
    change_path = root / "examples" / "toy_airline" / "api_change_spec.json"
    bundle = _run_pipeline(traj_path, change_path)
    write_json(demo_out / "exposure.json", bundle["exposures"][0])
    write_json(demo_out / "replay_plan.json", bundle["replay_plan"])
    write_json(demo_out / "mock_replay_results.json", bundle["mock_replay_results"])
    write_text(demo_out / "report.md", generate_report(bundle))
    click.echo(f"demo complete: {demo_out / 'report.md'}")


def _run_pipeline(trajectories: Path, changes: Path) -> dict[str, Any]:
    trajs = _load_trajectories(trajectories)
    specs = _load_changes(changes)
    exposures = [compute_exposure(t) for t in trajs if t.success]
    replay_plan = plan_replay(trajs, specs)
    mock_results = _mock_replay_all(trajs, specs)
    return {
        "trajectories": [t.model_dump() for t in trajs],
        "changes": [c.model_dump() for c in specs],
        "exposures": exposures,
        "replay_plan": replay_plan,
        "mock_replay_results": mock_results,
    }


def _mock_replay_all(
    trajectories: list[BaselineTrajectory],
    changes: list[APIChangeSpec],
) -> list[dict[str, Any]]:
    results = []
    for traj in trajectories:
        if not traj.success:
            continue
        for change in changes:
            results.append(mock_replay(traj, change))
    return results


def _load_trajectories(path: Path) -> list[BaselineTrajectory]:
    return [BaselineTrajectory.model_validate(x) for x in as_list(read_json(path))]


def _load_changes(path: Path) -> list[APIChangeSpec]:
    return [APIChangeSpec.model_validate(x) for x in as_list(read_json(path))]


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_demo_out() -> Path:
    cwd = Path.cwd()
    if cwd.name == "afc_gate" and (cwd / "examples").exists():
        return cwd.parent / "runs" / "afc_gate_demo"
    return cwd / "runs" / "afc_gate_demo"


if __name__ == "__main__":
    main()
