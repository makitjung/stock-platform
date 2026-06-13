#!/bin/bash
# 매일 아침 6:50 전체 파이프라인: 뉴스 수집 → 트렌드 수집/분석 → GitHub push

PLATFORM_DIR="/Users/jinhyugjung/Library/CloudStorage/OneDrive-개인/AI/stock-platform"
TREND_DIR="$PLATFORM_DIR/trend"
PYTHON="$HOME/.venvs/stock-platform/bin/python3"
NEWS_LOG="$PLATFORM_DIR/logs/news/news.log"
TREND_LOG="$PLATFORM_DIR/logs/trend/run.log"

echo "=== 일일 파이프라인 시작: $(date '+%Y-%m-%d %H:%M:%S') ===" | tee -a "$TREND_LOG"

# 1단계: 뉴스 수집 (trend/main.py의 push에서 같이 올라감)
echo "[1/3] 뉴스 수집..." | tee -a "$NEWS_LOG"
cd "$PLATFORM_DIR"
$PYTHON news/scripts/news_api.py >> "$NEWS_LOG" 2>&1
echo "[1/3] 뉴스 수집 완료" | tee -a "$NEWS_LOG"

# 2단계: 트렌드 전체 파이프라인 + GitHub push (news/latest_news.json도 포함)
echo "[2/3] 트렌드 파이프라인..." | tee -a "$TREND_LOG"
cd "$TREND_DIR"
$PYTHON main.py >> "$TREND_LOG" 2>&1
echo "=== 일일 파이프라인 완료: $(date '+%Y-%m-%d %H:%M:%S') ===" | tee -a "$TREND_LOG"

# 3단계: 헬스체크 요약 텔레그램 전송
echo "[3/3] 헬스체크 전송..." | tee -a "$TREND_LOG"
$PYTHON "$TREND_DIR/health_check.py" >> "$TREND_LOG" 2>&1
