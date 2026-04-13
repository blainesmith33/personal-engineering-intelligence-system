#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/kimberly/peis"
VENV_DIR="$REPO_DIR/.venv"
HOST="0.0.0.0"
PORT="8010"

cd "$REPO_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "ERROR: Missing virtual environment at $VENV_DIR"
  echo "Create it with: python3 -m venv .venv"
  read -r -p "Press Enter to close..."
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -c "import fastapi, uvicorn" >/dev/null 2>&1 || {
  echo "ERROR: Missing required packages in .venv"
  echo "Install with: pip install fastapi uvicorn"
  read -r -p "Press Enter to close..."
  exit 1
}

export PYTHONPATH="$REPO_DIR/src"

echo "Starting PEIS gateway..."
echo "Repo: $REPO_DIR"
echo "Python: $(which python)"
echo "Gateway URL: http://$HOST:$PORT"
echo "Launcher: peis.runtime.gateway.main"
echo

exec python -m peis.runtime.gateway.main