#!/usr/bin/env bash
# Run the edge benchmark on a Raspberry Pi 5 (Cortex-A76) and save results/edge_<cpu>.json.
# Copy the repo (with data/raw/ already fetched, so the Pi can stay offline), then:
#   bash scripts/bench_pi.sh
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv-pi
.venv-pi/bin/pip install -q -r requirements.txt
grep -m1 -E "Features" /proc/cpuinfo || true
.venv-pi/bin/python -m urja.edge.bench
