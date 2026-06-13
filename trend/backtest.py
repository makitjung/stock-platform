# 과거 강신호(7점↑) 종목의 신호일 이후 수익률을 집계해 신호 적중률을 검증하는 모듈

import json
import os
from datetime import datetime
import FinanceDataReader as fdr
import pandas as pd

HISTORY_DIR    = "history"
MIN_SCORE      = 7      # 강신호 기준
HORIZONS       = [1, 5]  # 신호일 이후 거래일 수
LOOKBACK_DATES = 40     # 최근 N개 스냅샷만 검토


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _build_name_to_code() -> dict:
    try:
        kospi  = fdr.StockListing("KOSPI")[["Code", "Name"]]
        kosdaq = fdr.StockListing("KOSDAQ")[["Code", "Name"]]
        alls   = pd.concat([kospi, kosdaq])
        return dict(zip(alls["Name"], alls["Code"]))
    except Exception:
        return {}


def _collect_signals() -> list:
    """history 분석 스냅샷에서 (날짜, 종목명) 강신호 목록 수집 (개별 종목만)."""
    try:
        dates = sorted(
            d for d in os.listdir(HISTORY_DIR)
            if os.path.isfile(os.path.join(HISTORY_DIR, d, "result_analysis.json"))
        )
    except FileNotFoundError:
        return []

    signals = []
    for d in dates[-LOOKBACK_DATES:]:
        data = load_json(os.path.join(HISTORY_DIR, d, "result_analysis.json"))
        for it in data.get("top50", []):
            if it.get("is_stock") is True and it.get("total_score", 0) >= MIN_SCORE:
                signals.append((d, it["keyword"]))
    return signals


def _forward_return(series: pd.DataFrame, date_str: str, horizon: int):
    """신호일(date_str) 종가 대비 horizon 거래일 후 종가 수익률(%). 미래 데이터 없으면 None."""
    try:
        idx = series.index
        # 신호일 이후(포함) 첫 거래일 위치
        pos = idx.searchsorted(pd.Timestamp(date_str))
        if pos >= len(idx) or pos + horizon >= len(idx):
            return None
        base = float(series["Close"].iloc[pos])
        fut  = float(series["Close"].iloc[pos + horizon])
        if base <= 0:
            return None
        return round((fut - base) / base * 100, 2)
    except Exception:
        return None


def _summarize(returns: list) -> dict:
    n = len(returns)
    if n == 0:
        return {"sample": 0, "win_rate": None, "avg_return": None}
    wins = [r for r in returns if r > 0]
    return {
        "sample":     n,
        "win_rate":   round(len(wins) / n * 100, 1),
        "avg_return": round(sum(returns) / n, 2),
        "avg_win":    round(sum(wins) / len(wins), 2) if wins else 0.0,
        "avg_loss":   round(sum(r for r in returns if r <= 0) / max(1, n - len(wins)), 2),
    }


def run():
    print("=== 신호 백테스트 시작 ===")
    today = datetime.today().strftime("%Y-%m-%d")

    signals = _collect_signals()
    if not signals:
        output = {"date": today, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                  "status": "데이터 누적 중", "horizons": {}, "samples": []}
        with open("result_backtest.json", "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print("강신호 표본 없음 — 데이터 누적 중")
        return output

    name_to_code = _build_name_to_code()
    earliest = min(d for d, _ in signals)

    # 종목별 가격 시계열을 한 번만 받아 재사용
    codes = {name_to_code.get(name) for _, name in signals}
    codes.discard(None)
    price_cache = {}
    for code in codes:
        try:
            df = fdr.DataReader(code, earliest, today)
            if not df.empty:
                price_cache[code] = df
        except Exception:
            continue

    # horizon별 수익률 수집
    horizon_returns = {h: [] for h in HORIZONS}
    samples = []  # 개별 신호 결과 (최신순 표시용)
    for date_str, name in signals:
        code = name_to_code.get(name)
        if not code or code not in price_cache:
            continue
        series = price_cache[code]
        rets = {h: _forward_return(series, date_str, h) for h in HORIZONS}
        for h in HORIZONS:
            if rets[h] is not None:
                horizon_returns[h].append(rets[h])
        if any(v is not None for v in rets.values()):
            samples.append({"date": date_str, "keyword": name,
                            "returns": {str(h): rets[h] for h in HORIZONS}})

    horizons_summary = {str(h): _summarize(horizon_returns[h]) for h in HORIZONS}

    # 베스트/워스트: 표본이 있는 가장 긴 horizon 기준 (긴 호라이즌이 비면 짧은 쪽으로 폴백)
    rank_h = next((str(h) for h in sorted(HORIZONS, reverse=True)
                   if horizon_returns[h]), None)
    if rank_h:
        rated = [s for s in samples if s["returns"].get(rank_h) is not None]
        best  = sorted(rated, key=lambda s: s["returns"][rank_h], reverse=True)[:5]
        worst = sorted(rated, key=lambda s: s["returns"][rank_h])[:5]
    else:
        rank_h, best, worst = None, [], []

    output = {
        "date": today,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "ok",
        "min_score": MIN_SCORE,
        "horizons": horizons_summary,
        "rank_horizon": rank_h,
        "best": best,
        "worst": worst,
        "total_signals": len(signals),
    }

    with open("result_backtest.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    for h in HORIZONS:
        s = horizons_summary[str(h)]
        print(f"  +{h}거래일: 표본 {s['sample']} | 승률 {s['win_rate']}% | 평균 {s['avg_return']}%")
    print("저장 완료 -> result_backtest.json")
    return output


if __name__ == "__main__":
    run()
