#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3.12 -m venv .venv-forge
.venv-forge/bin/python -m pip install -r requirements-dev.txt
exec .venv-forge/bin/python -m uvicorn forge.api:app --host 127.0.0.1 --port 8001
