#!/usr/bin/env bash
# ==============================================================================
# Jarvis AI - Environment Setup & Installation Script
# ==============================================================================
# Automates the setup of Python backend and Electron frontend environments:
# - Validates runtime prerequisites (Python >= 3.10, Node.js >= 18)
# - Creates Python virtual environment in backend/.venv if absent
# - Installs backend dependencies in editable development mode
# - Installs frontend npm packages and compiles TypeScript HUD
# ==============================================================================

set -euo pipefail

# ANSI color formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

log_info() {
    echo -e "${CYAN}[JARVIS SETUP]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[JARVIS SETUP] ✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[JARVIS SETUP] !${NC} $1"
}

log_error() {
    echo -e "${RED}[JARVIS SETUP] ✗${NC} $1" >&2
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

echo -e "${BOLD}${CYAN}"
echo "================================================================================"
echo "                   JARVIS AI SYSTEM SETUP & INSTALLATION                        "
echo "================================================================================"
echo -e "${NC}"

# ------------------------------------------------------------------------------
# 1. Prerequisite Validation
# ------------------------------------------------------------------------------
log_info "Verifying system prerequisites..."

# Check Python 3.10+
if ! command -v python3 &>/dev/null; then
    log_error "Python 3 is not installed or not available in PATH."
    exit 1
fi

PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "${PYTHON_VER}" | cut -d. -f1)
PYTHON_MINOR=$(echo "${PYTHON_VER}" | cut -d. -f2)

if [ "${PYTHON_MAJOR}" -lt 3 ] || { [ "${PYTHON_MAJOR}" -eq 3 ] && [ "${PYTHON_MINOR}" -lt 10 ]; }; then
    log_error "Python >= 3.10 is required. Found Python ${PYTHON_VER}."
    exit 1
fi
log_success "Python version ${PYTHON_VER} detected (>= 3.10 required)."

# Check Node.js 18+
if ! command -v node &>/dev/null; then
    log_error "Node.js is not installed or not available in PATH."
    exit 1
fi

NODE_VER=$(node -v | sed 's/^v//')
NODE_MAJOR=$(echo "${NODE_VER}" | cut -d. -f1)

if [ "${NODE_MAJOR}" -lt 18 ]; then
    log_error "Node.js >= 18 is required. Found Node.js v${NODE_VER}."
    exit 1
fi
log_success "Node.js version v${NODE_VER} detected (>= 18 required)."

# Check npm
if ! command -v npm &>/dev/null; then
    log_error "npm is not installed or not available in PATH."
    exit 1
fi
NPM_VER=$(npm -v)
log_success "npm version ${NPM_VER} detected."

# ------------------------------------------------------------------------------
# 2. Python Backend Virtual Environment & Dependencies
# ------------------------------------------------------------------------------
log_info "Configuring Python backend environment..."
cd "${REPO_ROOT}/backend"

if [ ! -d ".venv" ]; then
    log_info "Creating virtual environment in backend/.venv..."
    python3 -m venv .venv
    log_success "Created Python virtual environment."
else
    log_info "Existing virtual environment detected in backend/.venv."
fi

# Activate virtualenv for installation
# shellcheck disable=SC1091
source .venv/bin/activate

log_info "Upgrading pip, setuptools, and wheel in virtual environment..."
pip install --upgrade pip setuptools wheel --quiet || true

log_info "Installing Jarvis backend dependencies in editable mode (pip install -e \".[dev]\")..."
pip install -e ".[dev]"
log_success "Backend dependencies installed successfully."

# ------------------------------------------------------------------------------
# 3. Electron Frontend Dependencies & Build
# ------------------------------------------------------------------------------
log_info "Configuring Electron HUD frontend environment..."
cd "${REPO_ROOT}/frontend"

log_info "Installing npm packages (npm install)..."
npm install
log_success "Frontend npm packages installed."

log_info "Compiling TypeScript HUD and bundling assets (npm run build)..."
npm run build
log_success "Frontend compiled successfully into dist/."

# ------------------------------------------------------------------------------
# 4. Configuration & Directories
# ------------------------------------------------------------------------------
cd "${REPO_ROOT}"
if [ ! -d "config" ]; then
    mkdir -p config/plugins config/themes
    log_info "Created configuration directories."
fi

echo -e "\n${BOLD}${GREEN}================================================================================${NC}"
echo -e "${BOLD}${GREEN}                   JARVIS AI SETUP COMPLETED SUCCESSFULLY!                      ${NC}"
echo -e "${BOLD}${GREEN}================================================================================${NC}"
echo -e "To launch Jarvis in development mode, run:"
echo -e "  ${BOLD}${CYAN}./scripts/dev.sh${NC}\n"
