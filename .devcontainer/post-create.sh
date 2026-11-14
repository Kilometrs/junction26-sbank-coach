#!/usr/bin/env bash
# Runs once when the dev container is created: installs the Python and Node dependencies.
set -euo pipefail
cd "$(dirname "$0")/.."

# Named volumes are created owned by root.
sudo chown "$(id -u):$(id -g)" .venv mobile/node_modules

if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt

if [ -f mobile/package-lock.json ]; then
  (cd mobile && npm ci --no-audit --no-fund)
fi

echo
echo "Ready. Python $(.venv/bin/python -V | cut -d' ' -f2), Node $(node -v)."
[ -f .env ] || echo "No .env yet: cp .env.example .env and add your API key (the API won't start without one)."
[ -d data/tx ] || echo "No data/tx yet: run .venv/bin/python prep.py <path to Junction-2026-S-pankki>."
