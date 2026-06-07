#!/bin/bash
# Start Agora Dungeon OS server with Telegram integration
set -a
source "$(dirname "$0")/.env"
set +a
exec uvicorn agora.main:app --host 127.0.0.1 --port 8000 --log-level warning
