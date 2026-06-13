# 워치리스트 32종목의 장중 시세·거래량을 수집하고 가격 ±5% 또는 거래량 3배 급증 시 알람 엔진을 호출하는 모듈

import json
import os
import sys
import datetime
import FinanceDataReader as fdr

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)

from common.config import KR_STOCKS, US_STOCKS
from common import alarm_engine

OUT_PATH = os.path.join(BASE_DIR, "result_watchlist_live.json")

# config의 종목 별칭이 거래소 상장명과 다르거나(네이버→NAVER, JYP→JYP Ent.)
# KOSPI/KOSDAQ 목록에 없는 ETF는 종목코드를 직접 지정
KR_TICKER_OVERRIDE = {
    "네이버":   "035420",
    "JYP":      "035900",
    "금ETF":    "411060",  # ACE KRX금현물
    "은ETF":    "144600",  # KODEX 은선물(H)
    "구리ETF":  "138910",  # KODEX 구리선물(H)
}


def _kr_listing_maps():
    """KOSPI+KOSDAQ 상장 정보를 (name->info, code->info)로 구성 (1회 호출)."""
    by_name, by_code = {}, {}
    for market in ["KOSPI", "KOSDAQ"]:
        try:
            df = fdr.StockListing(market)
        except Exception as e:
            print(f"  [watchlist] {market} 조회 오류: {e}")
            continue
        for _, row in df.iterrows():
            try:
                vol = row.get("Volume")
                info = {
                    "ticker": str(row["Code"]),
                    "price":  int(row["Close"]) if row["Close"] == row["Close"] else None,
                    "change_rate": round(float(row["ChagesRatio"]), 2),
                    "volume": int(vol) if vol is not None and vol == vol else None,
                }
                by_name[str(row["Name"])] = info
                by_code[str(row["Code"])] = info
            except Exception:
                continue
    return by_name, by_code


def _datareader_quote(code: str):
    """상장목록에 없는 종목(ETF 등)의 시세를 DataReader 종가 2개로 계산. 거래량 포함."""
    start = (datetime.datetime.today() - datetime.timedelta(days=8)).strftime("%Y-%m-%d")
    try:
        df = fdr.DataReader(code, start)
        if df.empty or len(df) < 2:
            return None
        close = float(df["Close"].iloc[-1])
        prev  = float(df["Close"].iloc[-2])
        vol   = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else None
        return {
            "ticker": code,
            "price":  round(close, 2),
            "change_rate": round((close - prev) / prev * 100, 2) if prev > 0 else None,
            "volume": vol,
        }
    except Exception:
        return None


def _collect_kr() -> list:
    by_name, by_code = _kr_listing_maps()
    out = []
    for s in KR_STOCKS:
        name = s["name"]
        info = by_name.get(name)
        if not info:
            code = KR_TICKER_OVERRIDE.get(name)
            if code:
                info = by_code.get(code) or _datareader_quote(code)
        if not info:
            continue
        out.append({
            "name":        name,
            "ticker":      info["ticker"],
            "sector":      s.get("sector", ""),
            "price":       info["price"],
            "change_rate": info["change_rate"],
            "volume":      info.get("volume"),
            "market":      "KR",
        })
    return out


def _collect_us() -> list:
    """미국 종목 시세는 FDR로 수집 (FMP 무료 플랜이 대부분의 US 종목을 막음)."""
    start = (datetime.datetime.today() - datetime.timedelta(days=8)).strftime("%Y-%m-%d")
    out = []
    for s in US_STOCKS:
        try:
            df = fdr.DataReader(s["ticker"], start)
            if df.empty or len(df) < 2:
                continue
            close = float(df["Close"].iloc[-1])
            prev  = float(df["Close"].iloc[-2])
            vol   = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else None
            rate  = round((close - prev) / prev * 100, 2) if prev > 0 else None
        except Exception:
            continue
        out.append({
            "name":        s["name"],
            "ticker":      s["ticker"],
            "sector":      s.get("sector", ""),
            "price":       round(close, 2),
            "change_rate": rate,
            "volume":      vol,
            "market":      "US",
        })
    return out


def _refresh_baseline_if_needed(all_stocks: list) -> dict:
    """베이스라인 파일(오늘자)이 비어 있으면 종목별 DataReader로 어제 거래량을 채워서 저장."""
    baseline = alarm_engine.load_baseline()
    if baseline:
        return baseline

    print("  [watchlist] 거래량 베이스라인 신규 수집 (오늘 첫 호출)")
    start = (datetime.datetime.today() - datetime.timedelta(days=12)).strftime("%Y-%m-%d")
    fresh = {}
    for it in all_stocks:
        tk = it.get("ticker")
        if not tk:
            continue
        try:
            df = fdr.DataReader(tk, start)
            if df.empty or "Volume" not in df.columns:
                continue
            # 마지막 행이 오늘 날짜이면 장중 부분 거래량 → iloc[-2]가 전일.
            # 마지막 행이 오늘 이전이면(주말/공휴일/장 시작 전) iloc[-1]이 직전 완료된 거래일.
            today = datetime.date.today()
            last_date = df.index[-1].date()
            idx = -2 if (last_date == today and len(df) >= 2) else -1
            prev_vol = int(df["Volume"].iloc[idx])
            if prev_vol > 0:
                fresh[str(tk)] = prev_vol
        except Exception as e:
            print(f"    [baseline] {tk} 조회 실패: {e}")

    alarm_engine.save_baseline(fresh)
    print(f"  [watchlist] 베이스라인 {len(fresh)}종목 저장")
    return fresh


def run():
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    print("=== 워치리스트 실시간 시세 수집 시작 ===")

    kr = _collect_kr()
    us = _collect_us()
    all_stocks = kr + us
    print(f"  국내 {len(kr)}종목, 미국 {len(us)}종목 수집")

    # 알람: 가격 ±5% + 거래량 N배
    baseline = _refresh_baseline_if_needed(all_stocks)
    state    = alarm_engine.load_state()
    price_lines  = alarm_engine.check_price_spike(all_stocks, state)
    volume_lines = alarm_engine.check_volume_spike(all_stocks, baseline, state)
    alarm_engine.send_alerts(price_lines, volume_lines, [])
    alarm_engine.save_state(state)
    if price_lines or volume_lines:
        print(f"  [watchlist] 알람 전송 — 가격 {len(price_lines)}건, 거래량 {len(volume_lines)}건")

    output = {
        "date": today,
        "collected_at": now.strftime("%Y-%m-%d %H:%M"),
        "kr": kr,
        "us": us,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"저장 완료 -> result_watchlist_live.json")
    return output


if __name__ == "__main__":
    run()
