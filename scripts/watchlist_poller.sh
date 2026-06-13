#!/bin/bash
# cron(3분 주기)에서 워치리스트 폴러를 venv로 실행하고 로그를 남기는 래퍼

PLATFORM_DIR="$HOME/dev/stock-platform"
PYTHON="$HOME/.venvs/stock-platform/bin/python3"
LOG_DIR="$PLATFORM_DIR/logs/watchlist"
LOG_FILE="$LOG_DIR/poll.log"

mkdir -p "$LOG_DIR"

echo "" >> "$LOG_FILE"
$PYTHON "$PLATFORM_DIR/scripts/watchlist_poller.py" >> "$LOG_FILE" 2>&1
