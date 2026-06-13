#!/bin/bash
# 새 맥에서 stock-platform 파이프라인을 1회 부트스트랩 (venv + 패키지 + cron 등록)
set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
VENV="$HOME/.venvs/stock-platform"

echo "[1/3] venv 생성 ($VENV)"
if [ ! -d "$VENV" ]; then
    (/opt/homebrew/bin/python3 -m venv "$VENV" 2>/dev/null || python3 -m venv "$VENV")
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install -q -r requirements.txt

echo "[2/3] .env / 로그 폴더"
if [ ! -f .env ]; then
    echo "  .env 가 없습니다. NAVER/DART/FMP/TELEGRAM/YOUTUBE 키를 담은 .env 를 만들어 주세요."
fi
mkdir -p logs/trend logs/news

echo "[3/3] cron 등록"
bash install_cron.sh

echo ""
echo "완료. 코드=이 폴더, 발행 데이터=~/stock-platform-git(Vercel), 파이프라인=cron."
echo "뉴스봇은 ~/bin/stocknewsbot_launcher.sh + com.stocknewsbot.plist 로 별도 구동됩니다."
