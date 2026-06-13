# Google Trends 공식 RSS로 실시간 급상승 검색어를 수집하는 모듈 (selenium 미사용)

import json
import requests
from datetime import datetime
from lxml import etree

TRENDING_RSS = "https://trends.google.com/trending/rss?geo={geo}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def _localname(el) -> str:
    return etree.QName(el).localname


def get_trending_searches(geo="KR"):
    """Google Trends 급상승 검색어 RSS 파싱. [{title, geo, traffic}] 반환."""
    url = TRENDING_RSS.format(geo=geo)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        parser = etree.XMLParser(recover=True, encoding="utf-8")
        root = etree.fromstring(resp.content, parser=parser)
        if root is None:
            return []
    except Exception as e:
        print(f"  {geo} 수집 오류: {e}")
        return []

    results = []
    for item in root.findall(".//item"):
        title = ""
        traffic = ""
        for child in item:
            name = _localname(child)
            if name == "title":
                title = (child.text or "").strip()
            elif name == "approx_traffic":
                traffic = (child.text or "").strip()
        if title:
            results.append({"title": title, "geo": geo, "traffic": traffic})
    print(f"  {geo} 급상승 {len(results)}개 수집됨.")
    return results


def run(keywords=None):
    print("=== Google Trends (RSS) 수집 시작 ===")

    if keywords is None:
        try:
            with open("keywords_today.json", "r", encoding="utf-8") as f:
                keywords = json.load(f).get("keywords", [])
        except FileNotFoundError:
            print("keywords_today.json 없음. krx_symbols.py를 먼저 실행하세요.")
            keywords = []

    trending_kr = get_trending_searches("KR")
    trending_us = get_trending_searches("US")

    # 급상승 검색어와 내 키워드 매칭 (analyzer.py가 matched_keywords를 +5점으로 사용)
    matched = []
    seen = set()
    for trend in trending_kr + trending_us:
        title = trend.get("title", "")
        geo = trend.get("geo", "")
        tl = title.lower()
        for kw in keywords:
            if len(kw) < 2:
                continue
            kl = kw.lower()
            if (kl in tl or tl in kl) and (kw, title) not in seen:
                seen.add((kw, title))
                matched.append({
                    "keyword": kw,
                    "trending_title": title,
                    "geo": geo,
                    "source": "google_trends_rss",
                    "signal": "급상승검색어_등장",
                })

    output = {
        "date": datetime.today().strftime("%Y-%m-%d"),
        "trending_kr": trending_kr,
        "trending_us": trending_us,
        "matched_keywords": matched,
        "keyword_trends": [],  # RSS는 개별 키워드 관심도 미제공 (selenium 제거)
    }

    with open("result_google.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"수집 완료. 급상승 KR {len(trending_kr)}개, US {len(trending_us)}개, 키워드 매칭 {len(matched)}개 -> result_google.json")
    return output


if __name__ == "__main__":
    run()
