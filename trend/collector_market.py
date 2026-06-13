# KRX 시장 데이터(상한가/하한가/급등/급락)를 수집하는 모듈

import json
import os
import sys
import datetime
import FinanceDataReader as fdr

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)


def _fetch_market(market: str) -> dict:
    df = fdr.StockListing(market)
    if df is None or df.empty:
        return {"상한가": [], "하한가": [], "급등": [], "급락": []}

    df = df[df["Volume"] > 0].copy()
    df["rate"] = df["ChagesRatio"].astype(float)

    upper  = df[df["rate"] >= 29.0].sort_values("rate", ascending=False)
    lower  = df[df["rate"] <= -29.0].sort_values("rate", ascending=True)
    surge  = df[(df["rate"] >= 10) & (df["rate"] < 29.0)].sort_values("rate", ascending=False).head(30)
    plunge = df[(df["rate"] <= -10) & (df["rate"] > -29.0)].sort_values("rate", ascending=True).head(30)

    def rows(sub, n=30):
        return [
            {
                "ticker":      str(row["Code"]),
                "name":        str(row["Name"]),
                "close":       int(row["Close"]),
                "change_rate": round(float(row["rate"]), 2),
            }
            for _, row in list(sub.iterrows())[:n]
        ]

    return {
        "상한가": rows(upper),
        "하한가": rows(lower),
        "급등":   rows(surge),
        "급락":   rows(plunge),
    }


def _tickers(data: dict, market: str, category: str) -> set:
    """result_market.json에서 특정 시장/카테고리의 ticker set 반환."""
    try:
        return {s["ticker"] for s in data.get(market, {}).get(category, [])}
    except Exception:
        return set()


def _alert_new_entries(prev: dict, new: dict, today: str) -> None:
    """이전 수집 결과 대비 신규 상한가/급등 종목 발견 시 텔레그램 전송."""
    now = datetime.datetime.now()
    # 장중 시간(09:00~15:30)에만 알림
    market_open  = now.replace(hour=9,  minute=0,  second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if not (market_open <= now <= market_close):
        return

    prev_date = prev.get("date", "")
    same_day  = (prev_date == today)

    lines = []
    found_cats: set = set()
    for mkt_key, mkt_label in [("kospi", "KOSPI"), ("kosdaq", "KOSDAQ")]:
        for cat in ["상한가", "급등"]:
            # 당일 연속 수집 → 신규 진입 종목만 알림
            # 첫 수집 (전날 데이터) → 상한가만 알림
            if not same_day and cat == "급등":
                continue

            prev_set = _tickers(prev, mkt_key, cat)
            new_set  = _tickers(new,  mkt_key, cat)
            added    = new_set - prev_set

            if not added:
                continue

            # 신규 진입 종목 상세 정보 추출
            added_stocks = [
                s for s in new.get(mkt_key, {}).get(cat, [])
                if s["ticker"] in added
            ]
            for s in added_stocks:
                rate_str = f"+{s['change_rate']:.1f}%" if s['change_rate'] > 0 else f"{s['change_rate']:.1f}%"
                lines.append(f"  {mkt_label} {cat} 진입 | <b>{s['name']}</b> ({s['ticker']}) {rate_str}")
                found_cats.add(cat)

    if not lines:
        return

    cat_label = "/".join(sorted(found_cats)) if found_cats else "상한가/급등"
    try:
        from common.telegram import send_message
        header = f"🚨 <b>신규 {cat_label} 종목 알림</b> ({now.strftime('%H:%M')})"
        send_message(header + "\n" + "\n".join(lines))
        print(f"[market] 텔레그램 알림 전송: {len(lines)}건")
    except Exception as e:
        print(f"[market] 텔레그램 알림 실패: {e}")


def run():
    today = datetime.datetime.today().strftime("%Y-%m-%d")
    print(f"[market] 기준일: {today}")

    # 이전 결과 로드 (신규 진입 비교용)
    out_path = os.path.join(BASE_DIR, "result_market.json")
    prev_result: dict = {}
    try:
        with open(out_path, encoding="utf-8") as f:
            prev_result = json.load(f)
    except Exception:
        pass

    result: dict = {"date": today}
    for market in ["KOSPI", "KOSDAQ"]:
        print(f"  [market] {market} 수집 중...")
        data = _fetch_market(market)
        result[market.lower()] = data
        print(
            f"  [market] {market}: 상한가 {len(data['상한가'])}, "
            f"급등 {len(data['급등'])}, 급락 {len(data['급락'])}, 하한가 {len(data['하한가'])}"
        )

    # 신규 진입 종목 텔레그램 알림
    _alert_new_entries(prev_result, result, today)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[market] 저장 완료 -> result_market.json")

    # 당일 히스토리 파일에도 저장 (장중 갱신 + 장마감 후 최종 데이터 보존)
    hist_dir = os.path.join(BASE_DIR, "history", today)
    os.makedirs(hist_dir, exist_ok=True)
    hist_path = os.path.join(hist_dir, "result_market.json")
    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[market] 저장 완료 -> history/{today}/result_market.json")
