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

# 后端：优先使用项目 .venv 中的 uvicorn
UVICORN_CMD=""
if [[ -f "$ROOT_DIR/.venv/bin/uvicorn" ]]; then
  UVICORN_CMD="$ROOT_DIR/.venv/bin/uvicorn"
elif [[ -f "$ROOT_DIR/.venv/bin/activate" ]]; then
  # venv 存在但可能 uvicorn 未装，用 venv 的 python -m uvicorn
  UVICORN_CMD="$ROOT_DIR/.venv/bin/python -m uvicorn"
else
  UVICORN_CMD="$PYTHON_CMD -m uvicorn"
fi

start_backend() {
  echo "Starting backend..."
  cd "$BACKEND_DIR"
  # 若无历史数据则生成示例数据，保证首启即可用
  if [[ ! -f "$BACKEND_DIR/data/ssq_history.csv" ]] || [[ ! -f "$BACKEND_DIR/data/dlt_history.csv" ]]; then
    echo "No history data found, generating sample data..."
    "$PYTHON_CMD" "$BACKEND_DIR/scripts/gen_sample_data.py"
  fi
  if [[ -f "$BACKEND_PID_FILE" ]]; then
    if ps -p "$(cat "$BACKEND_PID_FILE")" > /dev/null 2>&1; then
      echo "Backend already running with PID $(cat "$BACKEND_PID_FILE")"
      return
    fi
  fi
  $UVICORN_CMD app.main:app --reload --port 8000 > "$BACKEND_DIR/.dev_backend.log" 2>&1 &
  echo $! > "$BACKEND_PID_FILE"
  echo "Backend started with PID $(cat "$BACKEND_PID_FILE")"
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
  # 使用 npx vite 确保使用项目内的 vite，nohup 防止脚本退出时进程被关
  nohup npx vite --host 127.0.0.1 --port 5173 > "$FRONTEND_DIR/.dev_frontend.log" 2>&1 &
  echo $! > "$FRONTEND_PID_FILE"
  echo "Frontend started with PID $(cat "$FRONTEND_PID_FILE")"
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

