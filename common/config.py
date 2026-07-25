# .env 로딩과 API 키 및 종목 리스트를 단일 출처로 노출하는 설정 모듈

import os
import json
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

# API 키는 stock_expert/.env 를 단일 출처로 읽는다(2026-07-25 통합).
# 두 레포가 NAVER·DART·TELEGRAM 키를 각자 두고 같은 무료 쿼터를 나눠 쓰고 있었고,
# 텔레그램은 봇 토큰이 서로 달라 채팅방이 둘로 갈려 있었다.
# 경로는 STOCK_EXPERT_ENV 로 덮어쓸 수 있다(레포 위치가 다른 환경 대비).
SHARED_ENV = Path(os.getenv("STOCK_EXPERT_ENV", ROOT.parent / "stock_expert" / ".env"))
load_dotenv(SHARED_ENV)
# 로컬 .env 가 남아 있으면 보조로만 읽는다(이미 로드된 값은 덮어쓰지 않음).
load_dotenv(ROOT / ".env")

NAVER_CLIENT_ID     = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
YOUTUBE_API_KEY     = os.getenv("YOUTUBE_API_KEY", "")
DART_API_KEY        = os.getenv("DART_API_KEY", "")
FMP_API_KEY         = os.getenv("FMP_API_KEY", "")
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID", "")

BASE_DIR  = str(ROOT)
TREND_DIR = str(ROOT / "trend")
NEWS_DIR  = str(ROOT / "news")
LOGS_DIR  = str(ROOT / "logs")

WATCHLIST_PATH = ROOT / "watchlist.json"


def _load_watchlist():
    """watchlist.json(단일 출처)에서 종목 리스트를 로드해 기존 스키마로 변환.
    KR: name/folder/market/sector, US: name/ticker/folder/sector. folder 생략 시 name 사용."""
    try:
        with open(WATCHLIST_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return [], []

    kr = []
    for s in data.get("kr", []):
        kr.append({
            "name":   s["name"],
            "folder": s.get("folder", s["name"]),
            "market": "KRX",
            "sector": s.get("sector", ""),
        })
    us = []
    for s in data.get("us", []):
        us.append({
            "name":   s["name"],
            "ticker": s.get("ticker", ""),
            "folder": s.get("folder", s["name"]),
            "sector": s.get("sector", ""),
        })
    return kr, us


KR_STOCKS, US_STOCKS = _load_watchlist()
ALL_STOCKS = KR_STOCKS + US_STOCKS
