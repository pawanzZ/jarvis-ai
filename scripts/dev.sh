#!/usr/bin/env bash
# ==============================================================================
# Jarvis AI - Development Runner Script
# ==============================================================================
# Concurrently launches the Python asyncio backend (ws://localhost:8765)
# and the Electron HUD frontend (npm run dev) with clean process cleanup on exit.
# ==============================================================================

set -e

# ANSI color formatting
BOLD="\033[1m"
CYAN="\033[0;36m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BOLD}${CYAN}"
echo "================================================================================"
echo "                     STARTING JARVIS AI DEVELOPMENT SERVER                      "
echo "================================================================================"
echo -e "${NC}"

# Clean child process cleanup on exit, interrupt, or termination
trap 'echo -e "\n${YELLOW}[JARVIS] Shutting down all background processes...${NC}"; kill $(jobs -p) 2>/dev/null || true' EXIT INT TERM

# 1. Start Python backend
echo -e "${CYAN}[JARVIS] Starting Python AsyncIO Backend (ws://localhost:8765)...${NC}"
cd "${REPO_ROOT}/backend"

# Use virtual environment if available, otherwise default to python3
if [ -f "${REPO_ROOT}/backend/.venv/bin/python3" ]; then
    "${REPO_ROOT}/backend/.venv/bin/python3" -m jarvis &
else
    python3 -m jarvis &
fi
BACKEND_PID=$!
echo -e "${GREEN}[JARVIS] Backend started with PID: ${BACKEND_PID}${NC}"

# 2. Start Electron HUD frontend
echo -e "${CYAN}[JARVIS] Starting Electron HUD Visualizer...${NC}"
cd "${REPO_ROOT}/frontend"
npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}[JARVIS] Frontend started with PID: ${FRONTEND_PID}${NC}"

echo -e "\n${BOLD}${GREEN}Jarvis AI is running! Press Ctrl+C to terminate both backend and frontend.${NC}\n"

# Wait for background processes
wait
