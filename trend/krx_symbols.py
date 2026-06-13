# KRX 코스피/코스닥 전체 종목을 FinanceDataReader로 가져와 거래량 상위 500개를 반환하는 모듈

import json
from datetime import datetime, timedelta
import FinanceDataReader as fdr


def load_my_keywords():
    try:
        with open("my_keywords.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        keywords = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                keywords.append(line)
        print(f"사용자 키워드 {len(keywords)}개 로드됨.")
        return keywords
    except FileNotFoundError:
        print("my_keywords.txt 없음. 기본 키워드 없이 진행.")
        return []


def get_recent_trading_day():
    today = datetime.today()
    for i in range(7):
        candidate = today - timedelta(days=i)
        if candidate.weekday() < 5:
            return candidate.strftime("%Y-%m-%d")
    return today.strftime("%Y-%m-%d")


def get_top500_keywords():
    print("=== KRX 종목 리스트 수집 시작 ===")

    trading_day = get_recent_trading_day()
    print(f"기준 거래일: {trading_day}")

    all_stocks = []
    name_to_code = {}  # 종목명 -> 6자리 코드 (대시보드 finance.naver 링크용)

    for market in ["KOSPI", "KOSDAQ"]:
        try:
            df = fdr.StockListing(market)
            for _, row in df.iterrows():
                name = str(row.get("Name", "")).strip()
                code = str(row.get("Code", "")).strip()
                volume = row.get("Volume", 0)
                try:
                    vol_int = int(volume) if volume == volume else 0
                except Exception:
                    vol_int = 0
                if name:
                    all_stocks.append({"name": name, "volume": vol_int})
                    if code:
                        name_to_code[name] = code
            print(f"{market} {len(df)}개 종목 수집됨.")
        except Exception as e:
            print(f"{market} 수집 오류: {e}")

    all_stocks.sort(key=lambda x: x["volume"], reverse=True)
    top500 = [s["name"] for s in all_stocks[:500]]
    print(f"거래량 상위 500개 선정 완료.")

    # 거래소 상장 종목명만 별도 저장 (is_stock 판별용, 테마 키워드 제외)
    all_listed_names = [s["name"] for s in all_stocks]
    with open("krx_stock_names.json", "w", encoding="utf-8") as f:
        json.dump({"date": datetime.today().strftime("%Y-%m-%d"), "names": all_listed_names}, f, ensure_ascii=False)

    # 종목명 -> 코드 맵 저장 (대시보드에서 finance.naver 종목 페이지로 링크하기 위함)
    with open("krx_codes.json", "w", encoding="utf-8") as f:
        json.dump({"date": datetime.today().strftime("%Y-%m-%d"), "codes": name_to_code}, f, ensure_ascii=False)

    my_keywords = load_my_keywords()
    combined = list(dict.fromkeys(top500 + my_keywords))

    with open("keywords_today.json", "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.today().strftime("%Y-%m-%d"),
            "trading_day": trading_day,
            "total": len(combined),
            "keywords": combined
        }, f, ensure_ascii=False, indent=2)

    print(f"완료. 상위 500개 + 내 키워드 {len(my_keywords)}개 = 총 {len(combined)}개.")
    return combined


if __name__ == "__main__":
    get_top500_keywords()


def run():
    return get_top500_keywords()
