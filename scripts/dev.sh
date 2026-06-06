#!/usr/bin/env bash
# =============================================================================
# Agora Development Server Script
# -----------------------------------------------------------------------------
# This script starts the full Agora development environment:
#   1. Start Docker Compose services (PostgreSQL, Redis, etc.)
#   2. Wait for PostgreSQL and Redis to become healthy
#   3. Start the Uvicorn ASGI server in the background
#   4. Start the Node.js frontend dev server (npm run dev)
#   5. Print accessible URLs for both servers
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Cleanup function to kill background processes on exit
cleanup() {
    log_info "Shutting down background processes..."
    [ -n "${UVICORN_PID:-}" ] && kill "$UVICORN_PID" 2>/dev/null && log_ok "Uvicorn stopped."
    [ -n "${NPM_PID:-}" ] && kill "$NPM_PID" 2>/dev/null && log_ok "npm dev server stopped."
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------------------
# Step 1: Start Docker Compose services
# ---------------------------------------------------------------------------
log_info "Step 1/5: Starting Docker Compose services..."

cd "$PROJECT_ROOT"
if [ -f docker-compose.yml ]; then
    docker compose up -d 2>&1 || {
        log_error "Failed to start Docker Compose services."
        exit 1
    }
    log_ok "Docker Compose services started."
else
    log_warn "No docker-compose.yml found. Assuming external services."
fi

# ---------------------------------------------------------------------------
# Step 2: Wait for PostgreSQL and Redis
# ---------------------------------------------------------------------------
log_info "Step 2/5: Waiting for services to become healthy..."

# PostgreSQL
PG_HOST="${AGORA_PG_HOST:-localhost}"
PG_PORT="${AGORA_PG_PORT:-5432}"
PG_USER="${AGORA_PG_USER:-agora}"
PG_DB="${AGORA_PG_DB:-agoradb}"
log_info "Waiting for PostgreSQL at $PG_HOST:$PG_PORT..."

for i in $(seq 1 30); do
    if command -v pg_isready &>/dev/null; then
        PGPASSWORD="${AGORA_PG_PASSWORD:-agora}" \
        pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" &>/dev/null && break
    else
        # Fallback: try a simple TCP connection
        timeout 1 bash -c "echo > /dev/tcp/$PG_HOST/$PG_PORT" 2>/dev/null && break
    fi
    if [ "$i" -eq 30 ]; then
        log_error "PostgreSQL did not become healthy within 30 seconds."
        exit 1
    fi
    sleep 1
done
log_ok "PostgreSQL is ready."

# Redis
REDIS_HOST="${AGORA_REDIS_HOST:-localhost}"
REDIS_PORT="${AGORA_REDIS_PORT:-6379}"
log_info "Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."

for i in $(seq 1 15); do
    timeout 1 bash -c "echo > /dev/tcp/$REDIS_HOST/$REDIS_PORT" 2>/dev/null && break
    if [ "$i" -eq 15 ]; then
        log_warn "Redis not detected on $REDIS_HOST:$REDIS_PORT. Continuing anyway."
    fi
    sleep 1
done
log_ok "Redis is ready."

# ---------------------------------------------------------------------------
# Step 3: Start Uvicorn ASGI server in the background
# ---------------------------------------------------------------------------
log_info "Step 3/5: Starting Uvicorn server in the background..."

VENV_DIR="$PROJECT_ROOT/.venv"
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
fi

APP_MODULE="${AGORA_APP_MODULE:-server.main:app}"
UVICORN_PORT="${AGORA_PORT:-8000}"

cd "$PROJECT_ROOT"
uvicorn "$APP_MODULE" --reload --host 0.0.0.0 --port "$UVICORN_PORT" &
UVICORN_PID=$!
log_ok "Uvicorn started (PID: $UVICORN_PID) on port $UVICORN_PORT"

# Give it a moment to start
sleep 2

# ---------------------------------------------------------------------------
# Step 4: Start Node.js frontend dev server
# ---------------------------------------------------------------------------
log_info "Step 4/5: Starting Node.js frontend dev server..."

FRONTEND_DIR="$PROJECT_ROOT/frontend"
if [ -d "$FRONTEND_DIR" ]; then
    cd "$FRONTEND_DIR"
    if [ -f package.json ]; then
        npm run dev &
        NPM_PID=$!
        log_ok "npm run dev started (PID: $NPM_PID)"
    else
        log_warn "No package.json found in $FRONTEND_DIR. Skipping."
    fi
else
    log_warn "No frontend directory found at $FRONTEND_DIR. Skipping."
fi

cd "$PROJECT_ROOT"

# ---------------------------------------------------------------------------
# Step 5: Print URLs
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Agora development servers running!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "  Backend API:     ${CYAN}http://localhost:${UVICORN_PORT}${NC}"
echo -e "  API Docs (Swagger): ${CYAN}http://localhost:${UVICORN_PORT}/docs${NC}"
echo -e "  API Docs (ReDoc):   ${CYAN}http://localhost:${UVICORN_PORT}/redoc${NC}"
echo -e "  Frontend:        ${CYAN}http://localhost:5173${NC}"
echo -e "  God Console:     ${CYAN}http://localhost:5173/god${NC}"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all servers."
echo ""

# Wait for all background processes
wait
