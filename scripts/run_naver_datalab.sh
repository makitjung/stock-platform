#!/bin/bash
# 1시간 주기 네이버 데이터랩 검색량 갱신 + GitHub push
# (정성 데이터라 장중 10분 주기는 과하다고 판단해 run_market.sh에서 분리)

TREND_DIR="$HOME/dev/stock-platform/trend"
PYTHON="$HOME/.venvs/stock-platform/bin/python3"
LOG="$HOME/dev/stock-platform/logs/trend/naver_datalab.log"

mkdir -p "$(dirname "$LOG")"
echo "--- 데이터랩 갱신: $(date '+%Y-%m-%d %H:%M:%S') ---" >> "$LOG"
cd "$TREND_DIR"

$PYTHON agent_runner.py collector_naver >> "$LOG" 2>&1
$PYTHON agent_runner.py push_data       >> "$LOG" 2>&1

echo "--- 완료: $(date '+%H:%M:%S') ---" >> "$LOG"
