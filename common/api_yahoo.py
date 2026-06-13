# Yahoo Finance RSS로 미국 종목 뉴스를 수집하는 공용 클라이언트 (무료, API 키 불필요)

import datetime
import requests
from lxml import etree

RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def fetch_us_news(ticker, limit=15):
    """미국 티커의 최신 뉴스(title, url, date, source) 리스트 반환."""
    try:
        resp = requests.get(RSS_URL.format(ticker=ticker), headers=HEADERS, timeout=10)
        resp.raise_for_status()
        parser = etree.XMLParser(recover=True, encoding="utf-8")
        root = etree.fromstring(resp.content, parser=parser)
        if root is None:
            return []
    except Exception as e:
        print(f"  [Yahoo RSS 오류] {ticker}: {e}")
        return []

    result = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link") or "").strip()
        if not title or not link:
            continue
        raw_date = (item.findtext("pubDate") or "").strip()
        try:
            dt = datetime.datetime.strptime(raw_date, "%a, %d %b %Y %H:%M:%S %z")
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.date.today().isoformat()
        result.append({"title": title, "url": link, "date": date_str, "source": "yahoo"})
    return result
