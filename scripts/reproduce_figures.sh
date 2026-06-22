#!/usr/bin/env bash
set -euo pipefail
if [ -z "${PYTHON:-}" ]; then
  if command -v python >/dev/null 2>&1; then PYTHON=python; else PYTHON=python3; fi
fi
"$PYTHON" scripts/offline_verify_results.py --section figures
