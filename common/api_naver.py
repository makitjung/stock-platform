# 네이버 데이터랩 및 뉴스 검색 API를 호출하는 공용 클라이언트

import re
import html
import requests
import datetime
from datetime import timedelta

from common.config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET

DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"
NEWS_URL    = "https://openapi.naver.com/v1/search/news.json"


def _headers(with_json=False):
    h = {
        "X-Naver-Client-Id":     NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    if with_json:
        h["Content-Type"] = "application/json"
    return h


def datalab_trend(keywords):
    """데이터랩 검색량 추이. keyword 그룹별 최근/직전 ratio 와 change_rate 반환."""
    end_date   = datetime.datetime.today()
    start_date = end_date - timedelta(days=30)
    body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate":   end_date.strftime("%Y-%m-%d"),
        "timeUnit":  "week",
        "keywordGroups": [{"groupName": kw, "keywords": [kw]} for kw in keywords],
    }
    resp = requests.post(DATALAB_URL, headers=_headers(with_json=True), json=body, timeout=15)
    if resp.status_code != 200:
        return []
    results = []
    for item in resp.json().get("results", []):
        periods = item["data"]
        if len(periods) >= 2:
            recent   = periods[-1]["ratio"]
            previous = periods[-2]["ratio"]
            change_rate = ((recent - previous) / previous) * 100 if previous > 0 else 0
            results.append({
                "keyword":     item["title"],
                "recent":      recent,
                "previous":    previous,
                "change_rate": round(change_rate, 1),
                "source":      "naver_datalab",
            })
    return results


def news_count(keyword):
    """키워드 뉴스 검색 총 건수만 반환."""
    params = {"query": keyword, "display": 100, "sort": "date"}
    resp = requests.get(NEWS_URL, headers=_headers(), params=params, timeout=10)
    if resp.status_code != 200:
        return {"keyword": keyword, "news_count": 0}
    return {"keyword": keyword, "news_count": resp.json().get("total", 0)}


def _parse_items(items):
    result = []
    for it in items:
        raw_date = it.get("pubDate", "")
        try:
            dt = datetime.datetime.strptime(raw_date, "%a, %d %b %Y %H:%M:%S %z")
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.date.today().isoformat()

        title = html.unescape(re.sub(r"<[^>]+>", "", it.get("title", "")).strip())
        link  = it.get("link", it.get("originallink", ""))
        result.append({"title": title, "url": link, "date": date_str, "source": "naver"})
    return result


def fetch_news(query, display=20):
    """뉴스 검색 결과 항목(title, url, date, source) 리스트 반환."""
    if not NAVER_CLIENT_ID:
        return []
    params = {"query": query, "display": display, "sort": "date"}
    try:
        resp = requests.get(NEWS_URL, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception as e:
        print(f"  [Naver API 오류] {query}: {e}")
        return []
    return _parse_items(items)


def fetch_news_paged(query, max_items=300, sort="date"):
    """start 파라미터로 페이지네이션하며 최대 max_items까지 뉴스 수집 (1년 backfill용).
    Naver 제약: display 1~100, start 1~1000."""
    if not NAVER_CLIENT_ID:
        return []
    out = []
    for start in range(1, 1001, 100):
        if len(out) >= max_items:
            break
        params = {"query": query, "display": 100, "start": start, "sort": sort}
        try:
            resp = requests.get(NEWS_URL, headers=_headers(), params=params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])
        except Exception as e:
            print(f"  [Naver API 오류] {query} (start={start}): {e}")
            break
        if not items:
            break
        out.extend(_parse_items(items))
    return out[:max_items]
