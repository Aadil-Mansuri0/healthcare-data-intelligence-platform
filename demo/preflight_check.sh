#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# Preflight Check — run this FIRST, before docker-compose, on YOUR machine
# (not in any sandbox). Catches the most common "it doesn't even start"
# issues before you waste time debugging inside Docker logs.
#
# Usage: bash demo/preflight_check.sh
# ═══════════════════════════════════════════════════════════════════════════

set -e
PASS="✅"
FAIL="❌"
WARN="⚠️ "
errors=0

echo "Healthcare Platform — Demo Mode Preflight Check"
echo "================================================="
echo ""

# ─── 1. Docker installed and running ───────────────────────────────────────
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        echo "$PASS Docker is installed and running"
    else
        echo "$FAIL Docker is installed but NOT running — start Docker Desktop (or 'sudo systemctl start docker' on Linux)"
        errors=$((errors+1))
    fi
else
    echo "$FAIL Docker is not installed — install from https://docs.docker.com/get-docker/"
    errors=$((errors+1))
fi

# ─── 2. Docker Compose available ───────────────────────────────────────────
if docker compose version &> /dev/null; then
    echo "$PASS Docker Compose (v2 plugin) available"
elif command -v docker-compose &> /dev/null; then
    echo "$WARN Only docker-compose v1 found — commands in this repo use 'docker-compose' syntax, should still work, but v2 ('docker compose') is recommended"
else
    echo "$FAIL Docker Compose not found — comes bundled with Docker Desktop; on Linux install the compose plugin separately"
    errors=$((errors+1))
fi

# ─── 3. Python 3.9+ available (for seeding the demo database) ─────────────
if command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "$PASS Python $PY_VERSION found"
else
    echo "$FAIL python3 not found — needed to run demo/seed_database.py"
    errors=$((errors+1))
fi

# ─── 4. Ports 3000 and 8000 free ───────────────────────────────────────────
for port in 3000 8000; do
    if lsof -i ":$port" &> /dev/null || netstat -an 2>/dev/null | grep -q ":$port .*LISTEN"; then
        echo "$WARN Port $port appears to be in use — docker-compose will fail to bind it. Stop whatever's using it, or edit the port mapping in docker/docker-compose.demo.yml"
    else
        echo "$PASS Port $port is free"
    fi
done

# ─── 5. Enough disk space (Docker images for this stack are ~1.5GB total) ──
AVAILABLE_GB=$(df -Pk . | tail -1 | awk '{print int($4/1024/1024)}')
if [ "$AVAILABLE_GB" -lt 5 ]; then
    echo "$WARN Only ${AVAILABLE_GB}GB free disk space — Docker image builds need ~3-5GB. May fail partway through."
else
    echo "$PASS ${AVAILABLE_GB}GB free disk space (sufficient)"
fi

# ─── 6. We're running from the repo root (paths in compose files are relative) ─
if [ ! -f "docker/docker-compose.demo.yml" ]; then
    echo "$FAIL This script must be run from the repo root (healthcare_advanced/), not from inside demo/. cd back up one level and re-run: bash demo/preflight_check.sh"
    errors=$((errors+1))
else
    echo "$PASS Running from the correct directory (repo root)"
fi

echo ""
echo "================================================="
if [ "$errors" -eq 0 ]; then
    echo "$PASS All checks passed. Next steps:"
    echo ""
    echo "   python3 demo/seed_database.py"
    echo "   docker-compose -f docker/docker-compose.demo.yml up --build"
    echo ""
    echo "Then open http://localhost:3000  (login: admin / Admin@123)"
else
    echo "$FAIL $errors check(s) failed — fix the items marked $FAIL above before proceeding."
    exit 1
fi
