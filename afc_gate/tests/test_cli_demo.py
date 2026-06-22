from pathlib import Path

from click.testing import CliRunner

from afc_gate.cli import main


def test_cli_demo_runs_without_api(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(main, ["demo", "--out-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    report = tmp_path / "report.md"
    assert report.exists()
    assert "potential_compliant_semantic_failure" in report.read_text(encoding="utf-8")
