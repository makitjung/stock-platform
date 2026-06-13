# 종목별 backfill JSON 사이드카를 모아 news/backfill_index.json(대시보드 소비용)을 생성

import json
import os
import sys
from datetime import datetime
from glob import glob

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)

from common.crash_notify import install_excepthook
install_excepthook("build_backfill_index")

from common.config import KR_STOCKS, US_STOCKS

NEWS_DIR   = os.path.join(PLATFORM_DIR, "news")
INDEX_PATH = os.path.join(NEWS_DIR, "backfill_index.json")
TOP_N      = 10   # 대시보드에 노출할 종목당 핵심 기사 건수


def _latest_backfill_for(market_sub: str, folder: str) -> dict | None:
    """news/<market_sub>/<folder>/backfill_1y_*.json 중 최신 파일 1건 반환."""
    pattern = os.path.join(NEWS_DIR, market_sub, folder, "backfill_1y_*.json")
    files = sorted(glob(pattern))
    if not files:
        return None
    try:
        with open(files[-1], encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [경고] {files[-1]} 로드 실패: {e}")
        return None


def _top_items(backfill: dict, limit: int = TOP_N) -> list:
    items = backfill.get("items", []) if backfill else []
    # add_stock.py가 score 내림차순으로 정렬해 저장하지만 안전망으로 재정렬
    items_sorted = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
    return items_sorted[:limit]


def build() -> dict:
    kr_out, us_out = [], []

    for s in KR_STOCKS:
        bf = _latest_backfill_for("국내", s["folder"])
        kr_out.append({
            "name":         s["name"],
            "sector":       s.get("sector", ""),
            "folder":       s["folder"],
            "generated_at": (bf or {}).get("generated_at", ""),
            "items":        _top_items(bf),
        })

    for s in US_STOCKS:
        bf = _latest_backfill_for("미국", s["folder"])
        us_out.append({
            "name":         s["name"],
            "ticker":       s.get("ticker", ""),
            "sector":       s.get("sector", ""),
            "folder":       s["folder"],
            "generated_at": (bf or {}).get("generated_at", ""),
            "items":        _top_items(bf),
        })

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "top_n":        TOP_N,
        "kr":           kr_out,
        "us":           us_out,
    }


def main():
    out = build()
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    nkr = sum(1 for s in out["kr"] if s["items"])
    nus = sum(1 for s in out["us"] if s["items"])
    print(f"backfill_index.json 갱신 완료 — KR {nkr}/{len(out['kr'])}, US {nus}/{len(out['us'])} 종목 보유")


if __name__ == "__main__":
    main()
