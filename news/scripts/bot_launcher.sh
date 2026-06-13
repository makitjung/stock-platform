#!/bin/bash
# launchd 전용 봇 런처 — 포그라운드로 실행 (launchd가 프로세스 관리)

# 로그 디렉토리 보장
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$SCRIPT_DIR/../../logs/news"

# stock-platform 통합 venv 사용 (common.config가 python-dotenv를 요구하므로 시스템 python 금지)
PYTHON="$HOME/.venvs/stock-platform/bin/python3"
if [ ! -x "$PYTHON" ]; then
    echo "[launcher] 오류: $PYTHON 없음. Mac Mini에서 venv를 먼저 생성하세요."
    exit 1
fi

echo "[launcher] Python: $PYTHON"
echo "[launcher] 시작: $(date)"

# 포그라운드 실행 (launchd KeepAlive가 재시작 관리)
exec "$PYTHON" "$SCRIPT_DIR/bot_server.py"
