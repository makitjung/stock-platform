# watchlist.json에 종목을 추가하고 최근 1년 중요 뉴스를 backfill하는 스크립트
#
# 사용법:
#   python3 add_stock.py "삼성전자" --market kr --sector "반도체"
#   python3 add_stock.py "엔비디아" --market us --ticker NVDA --sector "반도체/AI"
#
# 동작: watchlist.json에 추가(중복 시 스킵) → 최근 1년 뉴스 수집·중요도 점수·중복제거
#       → 상위 N건을 news/<국내|미국>/<folder>/backfill_1y_<오늘>.md 로 저장

import os
import re
import sys
import json
import argparse
from datetime import datetime, timedelta

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)

from common.api_naver import fetch_news_paged
from common.api_yahoo import fetch_us_news
from common.dedup import deduplicate

WATCHLIST_PATH = os.path.join(PLATFORM_DIR, "watchlist.json")
NEWS_DIR       = os.path.join(PLATFORM_DIR, "news")
TOP_N          = 20      # 종목당 보관 건수
DAYS_BACK      = 365

# ── 중요도 점수 사전 (이벤트성 키워드 → 가중) ────────────────────
EVENT_WEIGHTS = {
    # 실적·공시 (주가 직결, 높은 가중)
    "잠정실적": 5, "실적": 4, "영업이익": 4, "어닝": 4, "흑자": 3, "적자": 3,
    "공급계약": 5, "수주": 5, "단일판매": 4, "대규모": 3,
    "유상증자": 4, "무상증자": 3, "감자": 4, "자사주": 3, "자기주식": 3,
    "합병": 5, "인수": 4, "M&A": 5, "분할": 3, "최대주주": 4, "지분": 3,
    "전환사채": 3, "신주인수권": 3, "배당": 3,
    # 사업·제품
    "신제품": 3, "출시": 2, "계약": 3, "협약": 2, "공장": 2, "증설": 3, "투자": 2,
    "FDA": 5, "승인": 4, "임상": 4, "특허": 3, "수출": 2,
    # 시장 반응
    "목표주가": 4, "상향": 3, "하향": 3, "투자의견": 3, "분석": 1,
    "급등": 4, "급락": 4, "신고가": 4, "신저가": 3, "52주": 2,
    # 리스크
    "소송": 4, "횡령": 4, "배임": 4, "리콜": 4, "제재": 3, "규제": 3,
    "상장폐지": 5, "관리종목": 4, "거래정지": 4, "감리": 3,
}
# 신뢰도 높은 출처 (제목/링크에 포함 시 가점)
TRUSTED_SOURCES = ("한국경제", "매일경제", "서울경제", "연합뉴스", "이데일리",
                   "머니투데이", "조선비즈", "hankyung", "mk.co.kr", "sedaily",
                   "yna.co.kr", "edaily", "mt.co.kr", "Reuters", "Bloomberg")
# 무조건 포함할 핵심 이벤트 (점수 무관)
MUST_INCLUDE = ("잠정실적", "실적발표", "공급계약", "수주", "유상증자", "합병",
                "최대주주변경", "상장폐지", "FDA", "승인")


def _recency_bonus(date_str: str) -> int:
    """최근 30일 +3, 90일 +2, 180일 +1, 그 외 0."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return 0
    days = (datetime.today() - d).days
    if days <= 30:  return 3
    if days <= 90:  return 2
    if days <= 180: return 1
    return 0


def score_article(item: dict) -> int:
    text = (item.get("title", "") + " " + item.get("url", ""))
    score = sum(w for kw, w in EVENT_WEIGHTS.items() if kw in text)
    if any(s in text for s in TRUSTED_SOURCES):
        score += 2
    score += _recency_bonus(item.get("date", ""))
    return score


def _within_year(item: dict) -> bool:
    try:
        d = datetime.strptime(item.get("date", ""), "%Y-%m-%d")
    except Exception:
        return True  # 날짜 파싱 실패 시 일단 포함
    return d >= datetime.today() - timedelta(days=DAYS_BACK)


def collect_backfill(name: str, market: str, ticker: str = "") -> list:
    """최근 1년 뉴스 수집 → 중요도 점수 → 중복제거 → 상위 N건."""
    raw = []
    if market == "kr":
        # date(최신) + sim(관련도) 를 섞어 시간적으로 넓게 + 중요 기사 확보
        raw += fetch_news_paged(f"{name} 주가", max_items=200, sort="date")
        raw += fetch_news_paged(f"{name}",      max_items=200, sort="sim")
    else:  # us: 한국어명 네이버 + Yahoo(영문, 최근)
        raw += fetch_news_paged(f"{name} 주가", max_items=150, sort="date")
        raw += fetch_news_paged(f"{name}",      max_items=150, sort="sim")
        if ticker:
            raw += fetch_news_paged(f"{ticker} 주가", max_items=100, sort="sim")
            raw += fetch_us_news(ticker, limit=30)

    # 1년 이내 필터 + 점수
    recent = [it for it in raw if _within_year(it)]
    for it in recent:
        it["score"] = score_article(it)

    # 중복 제거 (제목 유사도)
    deduped = deduplicate(recent, threshold=0.72)

    # 무조건 포함 대상 분리
    must = [it for it in deduped if any(k in it.get("title", "") for k in MUST_INCLUDE)]
    rest = [it for it in deduped if it not in must]
    rest.sort(key=lambda x: (x["score"], x["date"]), reverse=True)

    seen, final = set(), []
    for it in must + rest:
        key = it.get("url", "")
        if key in seen:
            continue
        seen.add(key)
        final.append(it)
        if len(final) >= TOP_N:
            break
    return final


def save_backfill(folder: str, market: str, name: str, articles: list, ticker: str = "", sector: str = "") -> str:
    sub = "국내" if market == "kr" else "미국"
    out_dir = os.path.join(NEWS_DIR, sub, folder)
    os.makedirs(out_dir, exist_ok=True)
    today = datetime.today().strftime("%Y-%m-%d")
    path = os.path.join(out_dir, f"backfill_1y_{today}.md")

    lines = [f"# {name} 최근 1년 중요 뉴스 (backfill {today})\n",
             f"총 {len(articles)}건 (중요도순)\n"]
    for i, it in enumerate(articles, 1):
        lines.append(f"## {i}. {it.get('title','')}")
        lines.append(f"- 날짜: {it.get('date','')}  | 중요도: {it.get('score',0)}")
        lines.append(f"- 링크: {it.get('url','')}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # JSON 사이드카: build_backfill_index가 곧바로 읽을 수 있는 구조화 데이터
    json_path = os.path.join(out_dir, f"backfill_1y_{today}.json")
    payload = {
        "name":         name,
        "market":       market,
        "ticker":       ticker,
        "sector":       sector,
        "folder":       folder,
        "generated_at": today,
        "items": [
            {
                "title":  it.get("title", ""),
                "date":   it.get("date", ""),
                "url":    it.get("url", ""),
                "source": it.get("source", ""),
                "score":  int(it.get("score", 0)),
            }
            for it in articles
        ],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def add_to_watchlist(name, market, ticker, sector, folder) -> bool:
    with open(WATCHLIST_PATH, encoding="utf-8") as f:
        data = json.load(f)
    key = "kr" if market == "kr" else "us"
    if any(s.get("name") == name for s in data.get(key, [])):
        print(f"[스킵] '{name}'은 이미 watchlist에 있습니다.")
        return False
    entry = {"name": name, "sector": sector}
    if market == "us":
        entry = {"name": name, "ticker": ticker, "folder": folder or f"{ticker}_{name}", "sector": sector}
    elif folder:
        entry["folder"] = folder
    data.setdefault(key, []).append(entry)
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[추가] watchlist.json에 '{name}' 추가됨 ({key.upper()}).")
    return True


def main():
    ap = argparse.ArgumentParser(description="watchlist에 종목 추가 + 1년 중요 뉴스 backfill")
    ap.add_argument("name", help="종목명 (한국어)")
    ap.add_argument("--market", choices=["kr", "us"], required=True)
    ap.add_argument("--ticker", default="", help="미국 종목 티커")
    ap.add_argument("--sector", default="", help="섹터")
    ap.add_argument("--folder", default="", help="저장 폴더명 (생략 시 자동)")
    args = ap.parse_args()

    if args.market == "us" and not args.ticker:
        ap.error("미국 종목은 --ticker 가 필요합니다.")

    add_to_watchlist(args.name, args.market, args.ticker, args.sector, args.folder)

    folder = args.folder or (f"{args.ticker}_{args.name}" if args.market == "us" else args.name)
    print(f"최근 1년 중요 뉴스 수집 중: {args.name} ...")
    articles = collect_backfill(args.name, args.market, args.ticker)
    path = save_backfill(folder, args.market, args.name, articles,
                         ticker=args.ticker, sector=args.sector)
    print(f"[완료] {len(articles)}건 저장 -> {path}")
    if articles:
        print("상위 5건:")
        for it in articles[:5]:
            print(f"  - ({it['score']}점, {it['date']}) {it['title'][:50]}")


if __name__ == "__main__":
    main()
