import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_no_critical_secret_findings():
    subprocess.run([sys.executable, "scripts/scan_for_secrets.py", "--root", "."], cwd=ROOT, check=True)
    report = json.loads((ROOT / "docs/secret_scan_report.json").read_text(encoding="utf-8"))
    assert report["counts"]["critical"] == 0
