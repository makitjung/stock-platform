# OpenDART 공시 검색 API를 호출하는 공용 클라이언트

import requests
from datetime import datetime, timedelta

from common.config import DART_API_KEY

LIST_URL = "https://opendart.fss.or.kr/api/list.json"


def get_disclosure_count(keyword, days=7):
    """corp_name 키워드로 최근 N일 공시 건수 반환."""
    end_date   = datetime.today()
    start_date = end_date - timedelta(days=days)
    params = {
        "crtfc_key":  DART_API_KEY,
        "corp_name":  keyword,
        "bgn_de":     start_date.strftime("%Y%m%d"),
        "end_de":     end_date.strftime("%Y%m%d"),
        "page_count": 100,
    }
    try:
        resp = requests.get(LIST_URL, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == "000":
            return {
                "keyword":          keyword,
                "disclosure_count": int(data.get("total_count", 0)),
                "source":           "opendart",
            }
        return {"keyword": keyword, "disclosure_count": 0, "source": "opendart"}
    except Exception as e:
        print(f"DART 오류 ({keyword}): {e}")
        return {"keyword": keyword, "disclosure_count": 0, "source": "opendart"}
