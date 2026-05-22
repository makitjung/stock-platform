# KRX 시장 데이터(상한가/하한가/급등/급락)를 수집하는 모듈

import json
import os
import datetime
import FinanceDataReader as fdr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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


def run():
    today = datetime.datetime.today().strftime("%Y-%m-%d")
    print(f"[market] 기준일: {today}")

    result: dict = {"date": today}
    for market in ["KOSPI", "KOSDAQ"]:
        print(f"  [market] {market} 수집 중...")
        data = _fetch_market(market)
        result[market.lower()] = data
        print(
            f"  [market] {market}: 상한가 {len(data['상한가'])}, "
            f"급등 {len(data['급등'])}, 급락 {len(data['급락'])}, 하한가 {len(data['하한가'])}"
        )

    out_path = os.path.join(BASE_DIR, "result_market.json")
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
