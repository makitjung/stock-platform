# 증권사 리포트(네이버 리서치 종목/산업 + 미래에셋)를 수집해 워치리스트·신호 종목/섹터로 매칭하는 모듈

import json
import os
import re
import sys
import requests
from datetime import datetime
from urllib.parse import urljoin
from lxml import html as lh

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)

from common.config import KR_STOCKS

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
NAVER_BASE         = "https://finance.naver.com"
COMPANY_LIST_URL   = f"{NAVER_BASE}/research/company_list.naver"
INDUSTRY_LIST_URL  = f"{NAVER_BASE}/research/industry_list.naver"


def _norm_date(s: str) -> str:
    """'26.05.22' 또는 '2026-05-22' → '2026-05-22'."""
    s = s.strip()
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{2})", s)
    if m:
        return f"20{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    return s


def _fetch(url, euckr=False):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        if euckr:
            r.encoding = "euc-kr"
        return lh.fromstring(r.text)
    except Exception as e:
        print(f"  [reports] 수집 오류 {url}: {e}")
        return None


def fetch_naver_company():
    """네이버 리서치 종목분석: [{stock, title, broker, date, link, code}]."""
    doc = _fetch(COMPANY_LIST_URL, euckr=True)
    if doc is None:
        return []
    out = []
    for tr in doc.xpath('//table//tr'):
        tds = tr.xpath('./td')
        if len(tds) < 6:
            continue
        stock = (tds[0].text_content() or "").strip()
        title = (tds[1].text_content() or "").strip()
        broker = (tds[2].text_content() or "").strip()
        date = _norm_date(tds[4].text_content() or "")
        if not stock or not title:
            continue
        code = ""
        code_href = tds[0].xpath('.//a/@href')
        if code_href:
            m = re.search(r"code=(\d+)", code_href[0])
            if m:
                code = m.group(1)
        rlink = tds[1].xpath('.//a/@href')
        link = urljoin(COMPANY_LIST_URL, rlink[0]) if rlink else ""
        out.append({"stock": stock, "title": title, "broker": broker,
                    "date": date, "link": link, "code": code, "source": "네이버리서치"})
    return out


def fetch_naver_industry():
    """네이버 리서치 산업분석: [{sector, title, broker, date, link}]."""
    doc = _fetch(INDUSTRY_LIST_URL, euckr=True)
    if doc is None:
        return []
    out = []
    for tr in doc.xpath('//table//tr'):
        tds = tr.xpath('./td')
        if len(tds) < 5:
            continue
        sector = (tds[0].text_content() or "").strip()
        title = (tds[1].text_content() or "").strip()
        broker = (tds[2].text_content() or "").strip()
        date = _norm_date(tds[4].text_content() or "")
        if not title:
            continue
        rlink = tds[1].xpath('.//a/@href')
        link = urljoin(INDUSTRY_LIST_URL, rlink[0]) if rlink else ""
        out.append({"sector": sector, "title": title, "broker": broker,
                    "date": date, "link": link, "source": "네이버리서치(산업)"})
    return out


def fetch_mirae():
    """미래에셋 리서치 보드: [{title, date, broker, link}]."""
    url = "https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521"
    doc = _fetch(url, euckr=True)
    if doc is None:
        return []
    out = []
    for tr in doc.xpath('//table//tr'):
        tds = tr.xpath('./td')
        if len(tds) < 4:
            continue
        date = _norm_date(tds[0].text_content() or "")
        title = (tds[1].text_content() or "").strip()
        if not re.match(r"\d{4}-\d{2}-\d{2}", date) or not title:
            continue
        href = tds[1].xpath('.//a/@href')
        raw = href[0] if href else ""
        # javascript:view(...) 같은 JS 핸들러는 직접 링크가 불가하므로 리스트 페이지로 폴백
        if not raw or raw.lower().startswith("javascript:"):
            link = url
        else:
            link = urljoin(url, raw)
        out.append({"title": title, "date": date, "broker": "미래에셋증권",
                    "link": link, "source": "미래에셋"})
    return out


def _build_targets():
    """매칭 대상: 워치리스트 종목·섹터 + 트렌드 top50(신호) 종목·테마."""
    stocks = {s["name"] for s in KR_STOCKS}
    sectors = set()
    for s in KR_STOCKS:
        for tok in re.split(r"[/·\s]", s.get("sector", "")):
            if len(tok) >= 2:
                sectors.add(tok)

    # 트렌드 top50: is_stock는 종목, 그 외는 테마(섹터)로 추가
    try:
        with open(os.path.join(BASE_DIR, "result_analysis.json"), encoding="utf-8") as f:
            top = json.load(f).get("top50", [])
        for it in top:
            kw = it.get("keyword", "")
            if it.get("is_stock"):
                stocks.add(kw)
            elif len(kw) >= 2:
                sectors.add(kw)
    except Exception:
        pass
    return stocks, sectors


def run():
    print("=== 증권사 리포트 수집 시작 ===")
    target_stocks, target_sectors = _build_targets()

    company = fetch_naver_company()
    industry = fetch_naver_industry()
    mirae = fetch_mirae()
    print(f"  원본: 네이버종목 {len(company)}, 네이버산업 {len(industry)}, 미래에셋 {len(mirae)}")

    matched = []

    # 종목 리포트: 종목명 매칭
    for r in company:
        if r["stock"] in target_stocks:
            r["matched"] = r["stock"]
            r["kind"] = "종목"
            matched.append(r)

    # 산업 리포트: 섹터/제목에 타깃 섹터 키워드 포함
    for r in industry:
        hit = next((s for s in target_sectors if s in r["sector"] or s in r["title"]), None)
        if hit:
            r["matched"] = hit
            r["kind"] = "섹터"
            matched.append(r)

    # 미래에셋: 제목에 타깃 종목 또는 섹터 포함
    for r in mirae:
        hit = next((s for s in target_stocks if s in r["title"]), None) \
              or next((s for s in target_sectors if s in r["title"]), None)
        if hit:
            r["matched"] = hit
            r["kind"] = "종목" if hit in target_stocks else "섹터"
            matched.append(r)

    # 중복 제거(제목+증권사) 후 날짜순
    seen, dedup = set(), []
    for r in matched:
        key = (r.get("title", ""), r.get("broker", ""))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    dedup.sort(key=lambda x: x.get("date", ""), reverse=True)

    output = {
        "date": datetime.today().strftime("%Y-%m-%d"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "count": len(dedup),
        "reports": dedup[:40],
    }
    with open(os.path.join(BASE_DIR, "result_reports.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"매칭 리포트 {len(dedup)}건 저장 -> result_reports.json")
    for r in dedup[:8]:
        print(f"  [{r['source']}] {r.get('matched')} | {r['title'][:34]} ({r['broker']}, {r['date']})")
    return output


if __name__ == "__main__":
    run()
