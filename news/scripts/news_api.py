# Naver News API + Yahoo Finance RSS를 직접 호출하여 주식 뉴스를 수집하는 독립 모듈

import os
import sys
import json
import time
import html
import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import BASE_DIR, KR_STOCKS, US_STOCKS
from common.api_naver import fetch_news
from common.api_yahoo import fetch_us_news
from common.dedup import deduplicate
from common.crash_notify import install_excepthook
install_excepthook("news_api")

# ─── 상수 ─────────────────────────────────────────────────────
KR_NEWS_DIR = os.path.join(BASE_DIR, "국내")
US_NEWS_DIR = os.path.join(BASE_DIR, "미국")
MAX_ITEMS_PER_STOCK = 10   # 종목당 최대 뉴스 건수
DEDUP_THRESHOLD     = 0.72 # 제목 유사도 임계값


# ─── 단일 종목 수집 ────────────────────────────────────────────
def collect_kr_stock(stock: dict) -> list[dict]:
    """국내 종목 뉴스 수집: Naver API."""
    name = stock["name"]
    print(f"  수집 중: {name} (KR)")
    raw = fetch_news(name, display=25)
    deduped = deduplicate(raw, threshold=DEDUP_THRESHOLD)
    return deduped[:MAX_ITEMS_PER_STOCK]


def collect_us_stock(stock: dict) -> list[dict]:
    """미국 종목 뉴스 수집: Yahoo Finance RSS(영문) + Naver(국문)."""
    name   = stock["name"]
    ticker = stock["ticker"]
    print(f"  수집 중: {name} ({ticker})")

    yahoo_items = fetch_us_news(ticker, limit=20)
    naver_items = fetch_news(f"{ticker} {name}", display=10)
    combined    = yahoo_items + naver_items
    deduped     = deduplicate(combined, threshold=DEDUP_THRESHOLD)
    return deduped[:MAX_ITEMS_PER_STOCK]


# ─── 전체 수집 ─────────────────────────────────────────────────
def collect_all_news(today: Optional[str] = None) -> dict[str, list[dict]]:
    """
    전체 32개 종목 뉴스 수집.
    반환값: {종목명: [뉴스항목, ...]} 딕셔너리
    """
    if today is None:
        today = datetime.date.today().isoformat()

    all_news: dict[str, list[dict]] = {}

    print("[국내 종목 수집]")
    for stock in KR_STOCKS:
        items = collect_kr_stock(stock)
        all_news[stock["name"]] = items
        time.sleep(0.3)   # API rate limit 방지

    print("[미국 종목 수집]")
    for stock in US_STOCKS:
        items = collect_us_stock(stock)
        all_news[stock["name"]] = items
        time.sleep(0.3)

    return all_news


# ─── MD 파일 저장 ──────────────────────────────────────────────
def _stock_dir_for(stock_name: str) -> Optional[str]:
    """종목 이름 → 실제 저장 폴더 절대경로 반환."""
    for s in KR_STOCKS:
        if s["name"] == stock_name:
            return os.path.join(KR_NEWS_DIR, s["folder"])
    for s in US_STOCKS:
        if s["name"] == stock_name:
            return os.path.join(US_NEWS_DIR, s["folder"])
    return None


def save_news_to_files(all_news: dict[str, list[dict]], today: str) -> None:
    """수집된 뉴스를 종목별 MD 파일과 latest_news.md에 저장."""
    for stock_name, items in all_news.items():
        stock_dir = _stock_dir_for(stock_name)
        if not stock_dir:
            continue
        os.makedirs(stock_dir, exist_ok=True)

        # 날짜별 파일
        md_path = os.path.join(stock_dir, f"{today}.md")
        lines = [f"# {stock_name} 뉴스 — {today}\n"]
        if items:
            for it in items:
                lines.append(f"- [{it['title']}]({it.get('url','')})  ({it['source']})\n")
        else:
            lines.append("- 수집된 뉴스 없음\n")
        with open(md_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    # latest_news.md (전체 요약)
    latest_path = os.path.join(BASE_DIR, "latest_news.md")
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(f"# 주식 뉴스 최신본 — {today}\n\n")
        for stock_name, items in all_news.items():
            f.write(f"## {stock_name}\n")
            if items:
                for it in items:
                    f.write(f"- [{it['title']}]({it.get('url','')})\n")
            else:
                f.write("- 뉴스 없음\n")
            f.write("\n")

    print(f"[저장 완료] latest_news.md + {len(all_news)}개 종목 파일")
    save_news_to_json(all_news, today)


def save_news_to_json(all_news: dict[str, list[dict]], today: str) -> None:
    """수집된 뉴스를 latest_news.json으로 저장 (대시보드용)."""
    kr_data = [
        {"name": s["name"], "sector": s.get("sector", ""), "items": all_news.get(s["name"], [])}
        for s in KR_STOCKS
    ]
    us_data = [
        {"name": s["name"], "ticker": s.get("ticker", ""), "sector": s.get("sector", ""), "items": all_news.get(s["name"], [])}
        for s in US_STOCKS
    ]
    payload = {"date": today, "kr": kr_data, "us": us_data}
    json_path = os.path.join(BASE_DIR, "latest_news.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[저장 완료] latest_news.json")


# ─── 텔레그램 메시지 포맷 ─────────────────────────────────────
def format_telegram_message(all_news: dict[str, list[dict]], today: str) -> str:
    """텔레그램 전송용 HTML 메시지 생성."""
    total = sum(len(v) for v in all_news.values())
    lines = [f"<b>📰 주식 뉴스 브리핑 — {today}</b>\n총 {total}건\n"]

    kr_names = {s["name"] for s in KR_STOCKS}
    us_names = {s["name"] for s in US_STOCKS}

    lines.append("\n<b>🇰🇷 국내 종목</b>")
    for name in [s["name"] for s in KR_STOCKS]:
        items = all_news.get(name, [])
        if not items:
            continue
        lines.append(f"\n<b>{name}</b> ({len(items)}건)")
        for it in items[:3]:   # 종목당 최대 3건 표시 (전체는 파일에)
            title = it["title"][:50] + ("…" if len(it["title"]) > 50 else "")
            lines.append(f'• <a href="{it.get("url","")}">{html.escape(title)}</a>')

    lines.append("\n<b>🇺🇸 미국 종목</b>")
    for name in [s["name"] for s in US_STOCKS]:
        items = all_news.get(name, [])
        if not items:
            continue
        lines.append(f"\n<b>{name}</b> ({len(items)}건)")
        for it in items[:3]:
            title = it["title"][:50] + ("…" if len(it["title"]) > 50 else "")
            lines.append(f'• <a href="{it.get("url","")}">{html.escape(title)}</a>')

    return "\n".join(lines)


def run_news_alerts(all_news: dict) -> int:
    """수집된 뉴스에서 핵심 키워드 점수 임계값 이상 기사를 텔레그램으로 알림. 발송 건수 반환."""
    from common import alarm_engine
    state = alarm_engine.load_state()
    lines = alarm_engine.check_news_alerts(all_news, state)
    if lines:
        alarm_engine.send_alerts([], [], lines)
    alarm_engine.save_state(state)
    return len(lines)


if __name__ == "__main__":
    today = datetime.date.today().isoformat()
    print(f"=== 뉴스 수집 시작: {today} ===")
    all_news = collect_all_news(today)
    save_news_to_files(all_news, today)
    fired = run_news_alerts(all_news)
    if fired:
        print(f"[뉴스 알람] {fired}건 텔레그램 발송")
    msg = format_telegram_message(all_news, today)
    print("\n[텔레그램 메시지 미리보기]")
    print(msg[:500])
