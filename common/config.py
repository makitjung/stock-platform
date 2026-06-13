# .env 로딩과 API 키 및 종목 리스트를 단일 출처로 노출하는 설정 모듈

import os
import json
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
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
