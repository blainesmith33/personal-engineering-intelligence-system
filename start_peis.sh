#!/usr/bin/env bash
set -euo pipefail

cd /home/kimberly/peis
source .venv/bin/activate

echo "[PEIS] python: $(which python)"
echo "[PEIS] version: $(python -V 2>&1)"
echo "[PEIS] cli: ready"

exec bash
