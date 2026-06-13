# history/ 폴더에서 result_market.json이 누락되거나 잘못된 날짜를 FDR로 소급 수집하는 스크립트
#
# 실행:
#   cd ~/Library/CloudStorage/OneDrive-개인/AI/stock-platform/trend
#   ~/.venvs/stock-platform/bin/python3 backfill_market.py           # 누락 날짜만 소급
#   ~/.venvs/stock-platform/bin/python3 backfill_market.py --force   # 기존 파일 덮어쓰기
#
# 완료 후 push:
#   cd ~/stock-platform-git && git add -A && git commit -m "backfill market history" && git push

import json
import os
import sys
import FinanceDataReader as fdr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(BASE_DIR, "history")


def _fetch_one_market(date: str, market: str) -> dict:
    """FDR StockListing으로 특정 날짜의 시장 데이터를 수집."""
    empty = {"상한가": [], "하한가": [], "급등": [], "급락": []}
    try:
        df = fdr.StockListing(market, start=date, end=date)
    except Exception as e:
        print(f"    FDR 오류 ({market}): {e}")
        return empty

    if df is None or df.empty:
        print(f"    {market}: 데이터 없음 (휴장일 가능성)")
        return empty

    df = df[df["Volume"] > 0].copy()
    df["_rate"] = df["ChagesRatio"].astype(float)

    upper  = df[df["_rate"] >= 29.0].sort_values("_rate", ascending=False)
    lower  = df[df["_rate"] <= -29.0].sort_values("_rate", ascending=True)
    surge  = df[(df["_rate"] >= 10) & (df["_rate"] < 29.0)].sort_values("_rate", ascending=False).head(30)
    plunge = df[(df["_rate"] <= -10) & (df["_rate"] > -29.0)].sort_values("_rate", ascending=True).head(30)

    def rows(sub, n=30):
        return [
            {
                "ticker":      str(row["Code"]).zfill(6),
                "name":        str(row["Name"]),
                "close":       int(row["Close"]),
                "change_rate": round(float(row["_rate"]), 2),
            }
            for _, row in list(sub.iterrows())[:n]
        ]

    data = {
        "상한가": rows(upper),
        "하한가": rows(lower),
        "급등":   rows(surge),
        "급락":   rows(plunge),
    }
    print(
        f"    {market}: 상한가 {len(data['상한가'])}, "
        f"급등 {len(data['급등'])}, 급락 {len(data['급락'])}, 하한가 {len(data['하한가'])}"
    )
    return data


def backfill(target_dates: list | None = None, force: bool = False):
    """
    target_dates: None 이면 result_dates.json 기준 전체 소급.
                  ["2026-05-20", "2026-05-21"] 처럼 지정도 가능.
    force: True 이면 이미 존재하는 파일도 덮어씀.
    """
    if target_dates is None:
        dates_path = os.path.join(BASE_DIR, "result_dates.json")
        with open(dates_path, encoding="utf-8") as f:
            target_dates = json.load(f).get("dates", [])
    target_dates = sorted(target_dates)

    print(f"[backfill] 대상 날짜 {len(target_dates)}일: {target_dates}")

    if force:
        missing = target_dates
        print(f"[backfill] --force: 모든 날짜 재수집")
    else:
        missing = [d for d in target_dates
                   if not os.path.exists(os.path.join(HISTORY_DIR, d, "result_market.json"))]
        if not missing:
            print("[backfill] 모든 날짜에 result_market.json 이미 존재. 종료.")
            return

    print(f"[backfill] 소급 필요 날짜 {len(missing)}일: {missing}")

    for date in missing:
        print(f"\n[backfill] {date} 수집 중...")

        result = {"date": date}
        for market in ["KOSPI", "KOSDAQ"]:
            result[market.lower()] = _fetch_one_market(date, market)

        save_dir = os.path.join(HISTORY_DIR, date)
        os.makedirs(save_dir, exist_ok=True)
        out_path = os.path.join(save_dir, "result_market.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  저장 완료: history/{date}/result_market.json")

    print("\n[backfill] 소급 수집 완료.")
    print("[backfill] 다음 명령으로 GitHub에 업로드하세요:")
    print("  cd ~/stock-platform-git && git add -A && git commit -m 'backfill market history' && git push")


if __name__ == "__main__":
    backfill(force="--force" in sys.argv)
