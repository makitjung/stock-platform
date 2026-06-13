#!/bin/bash
# 매일 새벽 3시 cron에서 로그를 회전(*.log 1MB 초과 시 gz 압축, 30일 초과 시 삭제)

PLATFORM_DIR="$HOME/dev/stock-platform"
PYTHON="$HOME/.venvs/stock-platform/bin/python3"
LOG="$PLATFORM_DIR/logs/rotate.log"

mkdir -p "$(dirname "$LOG")"
$PYTHON "$PLATFORM_DIR/scripts/rotate_logs.py" >> "$LOG" 2>&1
