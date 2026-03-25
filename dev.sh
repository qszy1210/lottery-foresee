#!/usr/bin/env bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PID_FILE="$BACKEND_DIR/.dev_backend.pid"
FRONTEND_PID_FILE="$FRONTEND_DIR/.dev_frontend.pid"

# 优先选择 python3，如不存在则回退到 python
if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
else
  PYTHON_CMD="python"
fi

# 后端：优先使用 backend/.venv，其次 root/.venv
UVICORN_CMD=""
BACKEND_PYTHON="$PYTHON_CMD"
for VENV_DIR in "$BACKEND_DIR/.venv" "$ROOT_DIR/.venv"; do
  if [[ -f "$VENV_DIR/bin/activate" ]]; then
    BACKEND_PYTHON="$VENV_DIR/bin/python"
    if [[ -f "$VENV_DIR/bin/uvicorn" ]]; then
      UVICORN_CMD="$VENV_DIR/bin/uvicorn"
    else
      UVICORN_CMD="$VENV_DIR/bin/python -m uvicorn"
    fi
    break
  fi
done
if [[ -z "$UVICORN_CMD" ]]; then
  UVICORN_CMD="$PYTHON_CMD -m uvicorn"
fi

start_backend() {
  echo "Starting backend..."
  cd "$BACKEND_DIR"
  if [[ ! -f "$BACKEND_DIR/data/ssq_history.csv" ]] || [[ ! -f "$BACKEND_DIR/data/dlt_history.csv" ]]; then
    echo "Initializing history data from bundled dataset..."
    "$BACKEND_PYTHON" -c "from app.scripts.fetch_ssq import fetch_ssq_history; fetch_ssq_history()" 2>/dev/null || true
    "$BACKEND_PYTHON" -c "from app.scripts.fetch_dlt import fetch_dlt_history; fetch_dlt_history()" 2>/dev/null || true
  fi
  if [[ -f "$BACKEND_PID_FILE" ]]; then
    if ps -p "$(cat "$BACKEND_PID_FILE")" > /dev/null 2>&1; then
      echo "Backend already running with PID $(cat "$BACKEND_PID_FILE")"
      return
    fi
  fi
  $UVICORN_CMD app.main:app --reload --port 8000 > "$BACKEND_DIR/.dev_backend.log" 2>&1 &
  echo $! > "$BACKEND_PID_FILE"
  echo "Backend started with PID $(cat "$BACKEND_PID_FILE") -> http://127.0.0.1:8000"
}

start_frontend() {
  echo "Starting frontend..."
  cd "$FRONTEND_DIR"
  if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    echo "Installing frontend dependencies (first run)..."
    npm install
  fi
  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    if ps -p "$(cat "$FRONTEND_PID_FILE")" > /dev/null 2>&1; then
      echo "Frontend already running with PID $(cat "$FRONTEND_PID_FILE")"
      return
    fi
  fi
  FRONTEND_PORT=5173
  nohup npx vite --host 127.0.0.1 --port "$FRONTEND_PORT" > "$FRONTEND_DIR/.dev_frontend.log" 2>&1 &
  echo $! > "$FRONTEND_PID_FILE"
  echo "Frontend started with PID $(cat "$FRONTEND_PID_FILE") -> http://127.0.0.1:${FRONTEND_PORT}"
  echo ""
  echo "  Open http://127.0.0.1:${FRONTEND_PORT} in your browser"
  echo ""
}

stop_backend() {
  if [[ -f "$BACKEND_PID_FILE" ]]; then
    PID="$(cat "$BACKEND_PID_FILE")"
    if ps -p "$PID" > /dev/null 2>&1; then
      echo "Stopping backend PID $PID..."
      kill "$PID" || true
    fi
    rm -f "$BACKEND_PID_FILE"
  fi
}

stop_frontend() {
  if [[ -f "$FRONTEND_PID_FILE" ]]; then
    PID="$(cat "$FRONTEND_PID_FILE")"
    if ps -p "$PID" > /dev/null 2>&1; then
      echo "Stopping frontend PID $PID..."
      kill "$PID" || true
    fi
    rm -f "$FRONTEND_PID_FILE"
  fi
}

case "$1" in
  start)
    start_backend
    start_frontend
    ;;
  stop)
    stop_backend
    stop_frontend
    echo "All services stopped."
    ;;
  restart)
    stop_backend
    stop_frontend
    start_backend
    start_frontend
    ;;
  fetch-data)
    echo "Fetching history data..."
    cd "$BACKEND_DIR"
    "$PYTHON_CMD" -m app.scripts.fetch_ssq
    "$PYTHON_CMD" -m app.scripts.fetch_dlt
    echo "Done."
    ;;
  test)
    echo "Running backend tests..."
    cd "$BACKEND_DIR"
    pytest
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|fetch-data|test}"
    exit 1
    ;;
esac

