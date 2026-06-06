#!/usr/bin/env bash
set -euo pipefail
cd /home/vboxuser/agora/server
rm -f agora.db
export PYTHONPATH=.
export PYTHONUNBUFFERED=1
exec /home/vboxuser/agora/server/.venv/bin/uvicorn agora.main:app --host 127.0.0.1 --port 8000 --log-level debug 2>&1
