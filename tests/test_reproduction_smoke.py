import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_offline_verify_results_all():
    subprocess.run([sys.executable, "scripts/offline_verify_results.py", "--section", "all"], cwd=ROOT, check=True)


def test_reproduction_scripts_exist():
    for rel in [
        "scripts/reproduce_main_results.sh",
        "scripts/reproduce_figures.sh",
        "scripts/reproduce_audits.sh",
        "scripts/smoke_test.sh",
    ]:
        assert (ROOT / rel).exists()
