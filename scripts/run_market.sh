#!/bin/bash
# 장중 10분 주기 시세 갱신: 시장현황 + 워치리스트 실시간 + 가격/거래량 알람
# (GitHub push 는 2026-07-25 제거 — 산출물은 stock_expert 웹앱 광역스캔 탭에서 직접 읽는다)
# (collector_naver 데이터랩은 run_naver_datalab.sh로 1시간 주기 분리)

TREND_DIR="$HOME/dev/stock-platform/trend"
PYTHON="$HOME/.venvs/stock-platform/bin/python3"
LOG="$HOME/dev/stock-platform/logs/trend/market.log"

echo "--- 장중 갱신: $(date '+%H:%M:%S') ---" >> "$LOG"
cd "$TREND_DIR"

$PYTHON agent_runner.py collector_market         >> "$LOG" 2>&1
$PYTHON agent_runner.py collector_watchlist_live >> "$LOG" 2>&1

echo "--- 완료: $(date '+%H:%M:%S') ---" >> "$LOG"
