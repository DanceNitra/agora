#!/usr/bin/env bash
# =============================================================================
# Agora Bootstrap Script
# -----------------------------------------------------------------------------
# This script bootstraps the Agora development environment:
#   1. Check for Docker and Docker Compose
#   2. Start infrastructure services (PostgreSQL, Redis, etc.)
#   3. Create Python virtual environment
#   4. Install Python dependencies
#   5. Run Alembic database migrations
#   6. Seed initial agents into the database
#   7. Print success message with dashboard URL
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# Step 1: Check prerequisites
# ---------------------------------------------------------------------------
log_info "Step 1/7: Checking prerequisites..."

if ! command -v docker &>/dev/null; then
    log_error "Docker is not installed. Please install Docker first."
    log_info "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi
log_ok "Docker found: $(docker --version)"

if ! docker compose version &>/dev/null; then
    log_error "Docker Compose (v2) is required."
    log_info "Upgrade Docker Desktop or install docker-compose-plugin."
    exit 1
fi
log_ok "Docker Compose found: $(docker compose version)"

# ---------------------------------------------------------------------------
# Step 2: Start infrastructure services
# ---------------------------------------------------------------------------
log_info "Step 2/7: Starting infrastructure services..."

cd "$PROJECT_ROOT"
if [ -f docker-compose.yml ]; then
    docker compose up -d 2>&1 || {
        log_error "Failed to start Docker Compose services."
        exit 1
    }
else
    log_warn "No docker-compose.yml found at project root. Skipping."
fi
log_ok "Infrastructure services started."

# ---------------------------------------------------------------------------
# Step 3: Create Python virtual environment
# ---------------------------------------------------------------------------
log_info "Step 3/7: Creating Python virtual environment..."

VENV_DIR="$PROJECT_ROOT/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR" 2>&1 || {
        log_error "Failed to create virtual environment."
        exit 1
    }
    log_ok "Virtual environment created at $VENV_DIR"
else
    log_info "Virtual environment already exists. Skipping."
fi

# Activate
source "$VENV_DIR/bin/activate" || {
    log_error "Failed to activate virtual environment."
    exit 1
}
log_ok "Virtual environment activated."

# ---------------------------------------------------------------------------
# Step 4: Install Python dependencies
# ---------------------------------------------------------------------------
log_info "Step 4/7: Installing Python dependencies..."

REQUIREMENTS="$PROJECT_ROOT/requirements.txt"
if [ -f "$REQUIREMENTS" ]; then
    pip install --upgrade pip -q 2>&1
    pip install -r "$REQUIREMENTS" -q 2>&1 || {
        log_error "Failed to install dependencies from requirements.txt."
        exit 1
    }
    log_ok "Python dependencies installed."
else
    log_warn "No requirements.txt found at $REQUIREMENTS. Skipping."
fi

# ---------------------------------------------------------------------------
# Step 5: Run Alembic migrations
# ---------------------------------------------------------------------------
log_info "Step 5/7: Running Alembic migrations..."

ALEMBIC_DIR="$PROJECT_ROOT/server"
if [ -f "$ALEMBIC_DIR/alembic.ini" ]; then
    cd "$ALEMBIC_DIR"
    alembic upgrade head 2>&1 || {
        log_error "Alembic migrations failed."
        exit 1
    }
    cd "$PROJECT_ROOT"
    log_ok "Database migrations applied."
else
    log_warn "No alembic.ini found at $ALEMBIC_DIR. Skipping migrations."
    log_info "You can apply the schema manually via:"
    log_info "  psql -U agora -d agoradb -f server/agora/storage/schema.sql"
fi

# ---------------------------------------------------------------------------
# Step 6: Seed initial agents
# ---------------------------------------------------------------------------
log_info "Step 6/7: Seeding initial agents..."

SEED_SCRIPT="$PROJECT_ROOT/scripts/seed_agents.py"
if [ -f "$SEED_SCRIPT" ]; then
    python "$SEED_SCRIPT" 2>&1 || {
        log_warn "Seed script encountered an issue. Check logs above."
    }
    log_ok "Initial agents seeded."
else
    log_warn "No seed script found at $SEED_SCRIPT. Skipping."
    log_info "You can manually insert agents via the God Console later."
fi

# ---------------------------------------------------------------------------
# Step 7: Print success message
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Agora bootstrap complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "  Dashboard URL:  ${CYAN}http://localhost:8080${NC}"
echo -e "  API Base URL:   ${CYAN}http://localhost:8000/api/v1${NC}"
echo -e "  God Console:    ${CYAN}http://localhost:8080/god${NC}"
echo ""
echo -e "  Next steps:"
echo -e "    • Run ${YELLOW}./scripts/dev.sh${NC} to start the development server"
echo -e "    • Open the God Console to manage agents and tasks"
echo -e "    • Check docs/ for architecture and protocol documentation"
echo ""
