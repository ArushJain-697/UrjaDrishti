#!/usr/bin/env bash
# Rebuild everything from public data: fetch -> features -> train -> evaluate -> edge bench -> README numbers.
# The sealed test year is NOT scored here; that is a one-time `python -m urja.eval.run --final`.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
[ -x "$PY" ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; PY=.venv/bin/python; }
$PY -m urja.data.fetch          # ~2 min, cached in data/raw/ afterwards (offline from then on)
$PY -m urja.train
$PY -m urja.eval.run            # validation split
$PY -m urja.edge.bench
$PY -m pytest -q
$PY scripts/readme_numbers.py
echo "Done. Hourly schedules are in artifacts/schedules.parquet; results are in results/."
