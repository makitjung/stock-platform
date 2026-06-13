#!/bin/bash
# 경제 뉴스 매시간 갱신: 수집 → GitHub push

TREND_DIR="$HOME/dev/stock-platform/trend"
PYTHON="$HOME/.venvs/stock-platform/bin/python3"
LOG="$HOME/dev/stock-platform/logs/trend/econ_news.log"

echo "--- 경제뉴스 갱신: $(date '+%H:%M:%S') ---" >> "$LOG"
cd "$TREND_DIR"

$PYTHON agent_runner.py collector_econ_news >> "$LOG" 2>&1
$PYTHON agent_runner.py push_data          >> "$LOG" 2>&1

echo "--- 완료: $(date '+%H:%M:%S') ---" >> "$LOG"
