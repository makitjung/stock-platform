# 워치리스트 가격/거래량 급변 및 핵심 키워드 뉴스 발행 시 텔레그램 경고를 발송하는 룰 엔진

import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── 임계값 (기본값, 필요 시 조정) ──────────────────────────
PRICE_PCT_THRESHOLD   = 5.0   # ±5% 이상이면 알림
VOLUME_MULTIPLIER     = 3.0   # 전일 거래량 대비 N배 이상이면 알림
NEWS_SCORE_THRESHOLD  = 10    # EVENT_WEIGHTS 합산 점수 N점 이상이면 알림

STATE_PATH    = ROOT / "trend" / "_alarm_state.json"
BASELINE_PATH = ROOT / "trend" / "_alarm_baseline.json"

# ── 핵심 키워드 → 점수 (scripts/add_stock.py EVENT_WEIGHTS의 축약 버전) ─
MATERIAL_KEYWORDS = {
    # 실적·공시
    "잠정실적": 7, "실적": 4, "어닝": 4, "영업이익": 4, "흑자전환": 5, "적자전환": 5,
    "공급계약": 7, "수주": 6, "단일판매": 5, "대규모": 3,
    "유상증자": 5, "무상증자": 3, "감자": 5, "자사주": 4, "최대주주": 5,
    "합병": 6, "인수": 5, "M&A": 6, "분할": 4, "전환사채": 3,
    # 사업·제품
    "신제품": 3, "FDA": 7, "승인": 5, "임상": 5, "특허": 4, "증설": 4,
    # 시장 반응
    "목표주가": 4, "상향": 3, "급등": 5, "급락": 5, "신고가": 5, "신저가": 4,
    # 리스크
    "소송": 5, "횡령": 6, "배임": 5, "리콜": 5, "제재": 4, "규제": 3,
    "상장폐지": 8, "관리종목": 6, "거래정지": 6,
}


# ── 상태 파일 ──────────────────────────────────────────────
def _empty_state(today: str) -> dict:
    return {
        "date":          today,
        "price_fired":   [],   # 가격 ±5% 이미 알린 ticker 목록
        "volume_fired":  [],   # 거래량 3배 이미 알린 ticker 목록
        "news_fired":    [],   # 이미 알린 뉴스 (stock, title_hash) 튜플 → 문자열
    }


def load_state() -> dict:
    today = datetime.today().strftime("%Y-%m-%d")
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") != today:
            return _empty_state(today)
        # 누락 키 보강
        for k in ("price_fired", "volume_fired", "news_fired"):
            data.setdefault(k, [])
        return data
    except Exception:
        return _empty_state(today)


def save_state(state: dict) -> None:
    os.makedirs(STATE_PATH.parent, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ── 거래량 베이스라인 ───────────────────────────────────────
def load_baseline() -> dict:
    """trend/_alarm_baseline.json에서 오늘자 베이스라인을 로드. 날짜가 어제거나 없으면 빈 dict."""
    today = datetime.today().strftime("%Y-%m-%d")
    try:
        with open(BASELINE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") != today:
            return {}
        return data.get("volumes", {})
    except Exception:
        return {}


def save_baseline(volumes: dict) -> None:
    """{ticker: prev_volume} 저장. date는 오늘자로 고정."""
    payload = {
        "date":    datetime.today().strftime("%Y-%m-%d"),
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "volumes": volumes,
    }
    os.makedirs(BASELINE_PATH.parent, exist_ok=True)
    with open(BASELINE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ── 가격 급변 ──────────────────────────────────────────────
def check_price_spike(stocks: list, state: dict) -> list[str]:
    """change_rate가 ±PRICE_PCT_THRESHOLD를 처음 넘은 종목 알림 라인 반환."""
    fired = set(state.get("price_fired", []))
    lines = []
    for it in stocks:
        rate = it.get("change_rate")
        ticker = it.get("ticker") or it.get("name")
        if rate is None or abs(rate) < PRICE_PCT_THRESHOLD:
            continue
        if ticker in fired:
            continue
        arrow = "▲" if rate > 0 else "▼"
        flag  = "🇰🇷" if it.get("market") == "KR" else "🇺🇸"
        lines.append(f"  {flag} <b>{it.get('name','')}</b> ({ticker}) {arrow}{abs(rate):.2f}%")
        fired.add(ticker)
    state["price_fired"] = sorted(fired)
    return lines


# ── 거래량 급변 ──────────────────────────────────────────────
def check_volume_spike(stocks: list, baseline: dict, state: dict) -> list[str]:
    """현재 거래량이 베이스라인의 VOLUME_MULTIPLIER배 이상이면 알림."""
    fired = set(state.get("volume_fired", []))
    lines = []
    for it in stocks:
        ticker = it.get("ticker") or it.get("name")
        vol    = it.get("volume")
        base   = baseline.get(str(ticker))
        if not ticker or vol is None or not base or base <= 0:
            continue
        ratio = vol / base
        if ratio < VOLUME_MULTIPLIER:
            continue
        if ticker in fired:
            continue
        flag = "🇰🇷" if it.get("market") == "KR" else "🇺🇸"
        lines.append(
            f"  {flag} <b>{it.get('name','')}</b> ({ticker}) 거래량 {ratio:.1f}배 "
            f"({_fmt(vol)} / 전일 {_fmt(base)})"
        )
        fired.add(ticker)
    state["volume_fired"] = sorted(fired)
    return lines


def _fmt(n: int) -> str:
    return f"{int(n):,}"


# ── 뉴스 핵심 키워드 ────────────────────────────────────────
def score_news_title(title: str) -> int:
    """제목에 포함된 MATERIAL_KEYWORDS 점수 합."""
    return sum(pts for kw, pts in MATERIAL_KEYWORDS.items() if kw in title)


def check_news_alerts(all_news: dict, state: dict) -> list[str]:
    """all_news = {stock_name: [{title, url, date, source}, ...]} 형태에서
    NEWS_SCORE_THRESHOLD 이상 점수의 신규 기사를 알림."""
    fired = set(state.get("news_fired", []))
    lines = []
    for stock_name, items in (all_news or {}).items():
        if not items:
            continue
        for it in items:
            title = (it.get("title") or "").strip()
            if not title:
                continue
            score = score_news_title(title)
            if score < NEWS_SCORE_THRESHOLD:
                continue
            key = f"{stock_name}|{title[:60]}"
            if key in fired:
                continue
            url = it.get("url") or it.get("link") or ""
            lines.append(
                f"  <b>[{stock_name}]</b> ({score}점) "
                f'<a href="{url}">{_escape(title[:80])}</a>'
            )
            fired.add(key)
    state["news_fired"] = sorted(fired)
    return lines


def _escape(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ── 통합 발송 헬퍼 ───────────────────────────────────────────
def send_alerts(price_lines: list[str], volume_lines: list[str], news_lines: list[str]) -> None:
    """세 카테고리 알람을 묶어 텔레그램으로 전송. 빈 카테고리는 생략."""
    if not (price_lines or volume_lines or news_lines):
        return
    blocks = ["🚨 <b>워치리스트 알람</b>"]
    if price_lines:
        blocks.append("📈 <b>가격 ±5% 이탈</b>")
        blocks.extend(price_lines)
    if volume_lines:
        blocks.append("📊 <b>거래량 3배 이상 급증</b>")
        blocks.extend(volume_lines)
    if news_lines:
        blocks.append("📰 <b>핵심 키워드 뉴스</b>")
        blocks.extend(news_lines)
    text = "\n".join(blocks)
    try:
        from common.telegram import send_message
        send_message(text, tag="ALARM")
    except Exception as e:
        print(f"[alarm_engine] 텔레그램 전송 실패: {e}")
