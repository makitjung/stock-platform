# 일일 파이프라인 완료 후 텔레그램으로 헬스체크 요약을 전송하는 스크립트

import json
import os
import sys
from datetime import datetime

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def run():
    today = datetime.today().strftime("%Y-%m-%d")
    now   = datetime.now().strftime("%H:%M")

    analysis    = _load(os.path.join(BASE_DIR, "result_analysis.json"))
    market      = _load(os.path.join(BASE_DIR, "result_market.json"))
    econ_news   = _load(os.path.join(BASE_DIR, "result_econ_news.json"))
    news_latest = _load(os.path.join(PLATFORM_DIR, "news", "latest_news.json"))

    # 각 파일이 오늘 날짜인지 확인 (수집 성공 여부 판단)
    def ok(data: dict) -> str:
        return "✅" if data.get("date") == today else "❌"

    # 분석 요약
    total_analyzed = analysis.get("total_analyzed", 0)
    top50          = analysis.get("top50", [])
    strong_count   = sum(1 for x in top50 if x.get("total_score", 0) >= 7)
    mid_count      = sum(1 for x in top50 if 4 <= x.get("total_score", 0) < 7)

    # 시장 데이터 요약
    kospi  = market.get("kospi",  {})
    kosdaq = market.get("kosdaq", {})
    k_upper  = len(kospi.get("상한가",  []))
    k_surge  = len(kospi.get("급등",    []))
    kq_upper = len(kosdaq.get("상한가", []))
    kq_surge = len(kosdaq.get("급등",   []))

    # 뉴스 요약
    econ_total   = econ_news.get("total_articles", 0)
    news_count   = (
        sum(len(s.get("items", [])) for s in news_latest.get("kr", []))
        + sum(len(s.get("items", [])) for s in news_latest.get("us", []))
    )

    lines = [
        f"📋 <b>일일 파이프라인 완료</b> ({today} {now})",
        "━━━━━━━━━━━━━━━━━━━",
        f"{ok(analysis)} 트렌드 분석: {total_analyzed}종목 | 강신호 {strong_count}개 · 관심 {mid_count}개",
        f"{ok(market)} 시장 현황: KOSPI 상한가 {k_upper} · 급등 {k_surge} | KOSDAQ 상한가 {kq_upper} · 급등 {kq_surge}",
        f"{ok(econ_news)} 경제신문: {econ_total}건 수집",
        f"{'✅' if news_count > 0 else '❌'} 뉴스 아카이브: {news_count}건",
    ]

    try:
        from common.telegram import send_message
        send_message("\n".join(lines))
        print(f"[health_check] 텔레그램 전송 완료")
    except Exception as e:
        print(f"[health_check] 텔레그램 전송 실패: {e}")


if __name__ == "__main__":
    run()
