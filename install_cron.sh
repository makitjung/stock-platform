#!/bin/bash
# stock-platform cron 6개를 현재 프로젝트 경로로 (재)설치 (멱등). 새 맥에서도 그대로 동작.
set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
S="$PROJECT_DIR/scripts"
TMP="$(mktemp)"

# 기존 stock-platform cron 줄 제거 후 새 경로로 재작성
crontab -l 2>/dev/null | grep -v "stock-platform/scripts/" > "$TMP" || true
cat >> "$TMP" <<CRON
50 6 * * * $S/run_daily.sh >> /tmp/stock_daily.log 2>&1
*/10 9-15 * * 1-5 $S/run_market.sh
0 7-23 * * * $S/run_econ_news.sh >> $PROJECT_DIR/logs/trend/econ_news.log 2>&1
*/3 * * * * $S/watchlist_poller.sh
30 8-22 * * * $S/run_naver_datalab.sh
0 3 * * * $S/rotate_logs.sh
CRON

crontab "$TMP"
rm -f "$TMP"
echo "cron 6개 설치 완료:"
crontab -l | grep stock-platform
