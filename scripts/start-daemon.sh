#!/usr/bin/env bash
#
# start-daemon.sh - Start all Anaxa development services in daemon mode
#
# This script starts Anaxa services in the background without keeping
# the terminal connection. Logs are written to separate files.
#
# Must be run from the repo root directory.

set -e

export PATH="$HOME/.local/bin:$PATH"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

NGINX_PORT="${NGINX_PORT:-6200}"
FRONTEND_PORT="${FRONTEND_PORT:-6201}"
GATEWAY_PORT="${GATEWAY_PORT:-6202}"
LANGGRAPH_PORT="${LANGGRAPH_PORT:-6203}"

# ── Stop existing services ────────────────────────────────────────────────────

echo "Stopping existing services if any..."
pkill -f "langgraph dev" 2>/dev/null || true
pkill -f "uvicorn app.gateway.app:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "next start" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
nginx -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" -s quit 2>/dev/null || true
sleep 1
pkill -9 nginx 2>/dev/null || true
lsof -ti :"$LANGGRAPH_PORT" | xargs kill -9 2>/dev/null || true
lsof -ti :"$GATEWAY_PORT" | xargs kill -9 2>/dev/null || true
lsof -ti :"$FRONTEND_PORT" | xargs kill -9 2>/dev/null || true
./scripts/cleanup-containers.sh medrix-flow-sandbox 2>/dev/null || true
sleep 1

# ── Banner ────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo " Starting Anaxa in Daemon Mode"
echo "=========================================="
echo ""

# ── Config check ─────────────────────────────────────────────────────────────

if ! { \
        [ -n "$MEDRIX_FLOW_CONFIG_PATH" ] && [ -f "$MEDRIX_FLOW_CONFIG_PATH" ] || \
        [ -f backend/config.yaml ] || \
        [ -f config.yaml ]; \
    }; then
    echo "✗ No Anaxa config file found."
    echo "  Checked these locations:"
    echo "    - $MEDRIX_FLOW_CONFIG_PATH (when MEDRIX_FLOW_CONFIG_PATH is set)"
    echo "    - backend/config.yaml"
    echo "    - ./config.yaml"
    echo ""
    echo "  Run 'make bootstrap' from the repo root, then configure model API keys in the web UI."
    exit 1
fi

# ── Auto-upgrade config ──────────────────────────────────────────────────

"$REPO_ROOT/scripts/config-upgrade.sh"

# ── Cleanup on failure ───────────────────────────────────────────────────────

cleanup_on_failure() {
    echo "Failed to start services, cleaning up..."
    pkill -f "langgraph dev" 2>/dev/null || true
    pkill -f "uvicorn app.gateway.app:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "next start" 2>/dev/null || true
    pkill -f "next-server" 2>/dev/null || true
    nginx -c "$REPO_ROOT/docker/nginx/nginx.local.conf" -p "$REPO_ROOT" -s quit 2>/dev/null || true
    sleep 1
    pkill -9 nginx 2>/dev/null || true
    lsof -ti :"$LANGGRAPH_PORT" | xargs kill -9 2>/dev/null || true
    lsof -ti :"$GATEWAY_PORT" | xargs kill -9 2>/dev/null || true
    lsof -ti :"$FRONTEND_PORT" | xargs kill -9 2>/dev/null || true
    echo "✓ Cleanup complete"
}

trap cleanup_on_failure INT TERM

# ── Start services ────────────────────────────────────────────────────────────

mkdir -p logs

echo "Starting LangGraph + Gateway + Frontend in parallel..."

nohup sh -c "cd backend && NO_COLOR=1 uv run langgraph dev --no-browser --allow-blocking --no-reload --port \"$LANGGRAPH_PORT\" > ../logs/langgraph.log 2>&1" &
nohup sh -c "cd backend && PYTHONPATH=. uv run uvicorn app.gateway.app:app --host \"\${GATEWAY_HOST:-127.0.0.1}\" --port \"$GATEWAY_PORT\" > ../logs/gateway.log 2>&1" &
nohup sh -c "cd frontend && pnpm exec next dev --webpack --port \"$FRONTEND_PORT\" > ../logs/frontend.log 2>&1" &

LANGGRAPH_READY=false
GATEWAY_READY=false
FRONTEND_READY=false
TIMEOUT=120
elapsed=0
interval=1

while [ "$elapsed" -lt "$TIMEOUT" ]; do
    if ! $LANGGRAPH_READY && lsof -nP -iTCP:"$LANGGRAPH_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
        LANGGRAPH_READY=true
        echo "  ✓ LangGraph ready on localhost:${LANGGRAPH_PORT} (${elapsed}s)"
    fi
    if ! $GATEWAY_READY && lsof -nP -iTCP:"$GATEWAY_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
        GATEWAY_READY=true
        echo "  ✓ Gateway ready on localhost:${GATEWAY_PORT} (${elapsed}s)"
    fi
    if ! $FRONTEND_READY && lsof -nP -iTCP:"$FRONTEND_PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
        FRONTEND_READY=true
        echo "  ✓ Frontend ready on localhost:${FRONTEND_PORT} (${elapsed}s)"
    fi
    if $LANGGRAPH_READY && $GATEWAY_READY && $FRONTEND_READY; then
        break
    fi
    printf "\r  Waiting for services... %ds" "$elapsed"
    sleep "$interval"
    elapsed=$((elapsed + interval))
done
printf "\r  %-60s\r" ""

FAILED=false
if ! $LANGGRAPH_READY; then
    FAILED=true
    echo "✗ LangGraph failed to start on port ${LANGGRAPH_PORT} after ${TIMEOUT}s"
    tail -60 logs/langgraph.log
    if grep -qE "config_version|outdated|Environment variable .* not found|KeyError|ValidationError|config\.yaml" logs/langgraph.log 2>/dev/null; then
        echo ""
        echo "  Hint: This may be a configuration issue. Try running 'make config-upgrade' to update your config.yaml."
    fi
fi
if ! $GATEWAY_READY; then
    FAILED=true
    echo "✗ Gateway API failed to start on port ${GATEWAY_PORT} after ${TIMEOUT}s"
    tail -60 logs/gateway.log
    echo ""
    echo "  Hint: Try running 'make config-upgrade' to update your config.yaml with the latest fields."
fi
if ! $FRONTEND_READY; then
    FAILED=true
    echo "✗ Frontend failed to start on port ${FRONTEND_PORT} after ${TIMEOUT}s"
    tail -60 logs/frontend.log
fi
if $FAILED; then
    cleanup_on_failure
    exit 1
fi

echo "Starting Nginx reverse proxy..."
nohup sh -c 'nginx -g "daemon off;" -c "$1/docker/nginx/nginx.local.conf" -p "$1" > logs/nginx.log 2>&1' _ "$REPO_ROOT" &
./scripts/wait-for-port.sh "$NGINX_PORT" 10 "Nginx" || {
    echo "✗ Nginx failed to start. Last log output:"
    tail -60 logs/nginx.log
    cleanup_on_failure
    exit 1
}
echo "✓ Nginx started on localhost:${NGINX_PORT}"

# ── Ready ─────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo " Anaxa is running in daemon mode!"
echo "=========================================="
echo ""
echo " 🌐 Application: http://localhost:${NGINX_PORT}"
echo " 📡 API Gateway: http://localhost:${NGINX_PORT}/api/*"
echo " 🤖 LangGraph: http://localhost:${NGINX_PORT}/api/langgraph/*"
echo ""
echo " 📋 Logs:"
echo " - LangGraph: logs/langgraph.log"
echo " - Gateway: logs/gateway.log"
echo " - Frontend: logs/frontend.log"
echo " - Nginx: logs/nginx.log"
echo ""
echo " 🛑 Stop daemon: make stop"
echo ""
