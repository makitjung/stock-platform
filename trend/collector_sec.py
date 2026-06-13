# SEC EDGAR API로 미국 종목 공시 건수를 수집하는 모듈

import json
import time
import requests
from datetime import datetime, timedelta


HEADERS = {
    "User-Agent": "stock-trend-collector contact@example.com"
}


def search_company(keyword):
    """SEC EDGAR에서 회사명으로 CIK 코드 검색"""
    url = "https://efts.sec.gov/LATEST/search-index?q=%22{}%22&dateRange=custom&startdt={}&enddt={}&hits.hits._source=period_of_report,entity_name,file_date,form_type".format(
        requests.utils.quote(keyword),
        (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d"),
        datetime.today().strftime("%Y-%m-%d")
    )
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return {"keyword": keyword, "filing_count": 0, "source": "sec_edgar"}
        data = response.json()
        total = data.get("hits", {}).get("total", {}).get("value", 0)
        return {
            "keyword": keyword,
            "filing_count": total,
            "source": "sec_edgar"
        }
    except Exception as e:
        print(f"SEC 오류 ({keyword}): {e}")
        return {"keyword": keyword, "filing_count": 0, "source": "sec_edgar"}


def run(keywords=None):
    print("=== SEC EDGAR 공시 수집 시작 ===")

    if keywords is None:
        try:
            with open("keywords_today.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            keywords = data.get("keywords", [])
        except FileNotFoundError:
            print("keywords_today.json 없음. krx_symbols.py를 먼저 실행하세요.")
            return {}

    # 영문 키워드만 대상
    english_keywords = [kw for kw in keywords if kw.isascii() and len(kw) > 1]
    print(f"대상 키워드 {len(english_keywords)}개 (영문 종목명)")

    results = []
    for i, kw in enumerate(english_keywords):
        result = search_company(kw)
        if result["filing_count"] > 0:
            results.append(result)
        time.sleep(0.3)
        if (i + 1) % 10 == 0:
            print(f"진행중... {i+1}/{len(english_keywords)}")

    results.sort(key=lambda x: x["filing_count"], reverse=True)

    output = {
        "date": datetime.today().strftime("%Y-%m-%d"),
        "sec": results
    }

    with open("result_sec.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"수집 완료. 공시 있는 종목 {len(results)}개 저장 -> result_sec.json")
    return output


if __name__ == "__main__":
    run()
