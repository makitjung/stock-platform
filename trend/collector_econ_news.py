# 한경·매경 RSS + Naver News API를 병합해 중요 경제 기사를 수집하는 모듈

import json
import re
import requests
import feedparser
from datetime import datetime, timezone, timedelta

from common.config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET

KST = timezone(timedelta(hours=9))
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# ──────────────────────────────────────────────
# 중요도 스코어 사전 (키워드 → 점수)
# 시황 키워드 무관하게 기사 자체 중요도 측정용
# ──────────────────────────────────────────────
IMPORTANCE_MAP = {
    # 속보/단독
    "속보": 4, "단독": 3, "긴급": 4, "Breaking": 3,
    # 거시경제
    "금리": 3, "기준금리": 3, "환율": 3, "인플레이션": 3, "CPI": 3,
    "GDP": 3, "무역": 2, "관세": 3, "경기침체": 3, "침체": 2,
    "연준": 3, "Fed": 3, "FOMC": 3, "ECB": 2, "BOJ": 2, "한국은행": 2,
    # 시장
    "증시": 2, "코스피": 2, "코스닥": 2, "나스닥": 2, "다우": 2, "S&P": 2,
    "급등": 3, "급락": 3, "폭등": 3, "폭락": 3, "신고가": 3, "신저가": 3,
    "붕괴": 3, "충격": 2, "쇼크": 3, "위기": 2,
    # 기업 액션
    "실적": 2, "어닝": 2, "흑자": 2, "적자": 2, "영업이익": 2,
    "계약": 2, "수주": 2, "인수": 2, "합병": 2, "M&A": 3,
    "상장": 2, "IPO": 3, "증자": 2, "배당": 2, "자사주": 2,
    "목표주가": 2, "상향": 2, "하향": 2,
    # 섹터
    "반도체": 2, "AI": 2, "인공지능": 2, "배터리": 2, "전기차": 2,
    "바이오": 2, "제약": 2, "방산": 2, "원자재": 2, "유가": 2,
    "원유": 2, "금값": 2, "구리": 2, "달러": 2,
    # 지정학
    "전쟁": 2, "갈등": 1, "제재": 2, "협상": 1, "합의": 1,
}

# Naver News API로 검색할 광범위 금융 키워드 (시황 무관)
NAVER_SEARCH_QUERIES = [
    "증시 오늘", "코스피 코스닥", "미국증시", "나스닥",
    "금리 환율", "기업실적", "반도체 주가", "AI 관련주",
    "경제 뉴스", "무역 관세", "유가 원자재", "바이오 제약",
]

RSS_FEEDS = [
    {"source": "한국경제", "url": "https://www.hankyung.com/feed/finance"},
    {"source": "한국경제", "url": "https://www.hankyung.com/feed/economy"},
    {"source": "한국경제", "url": "https://www.hankyung.com/feed/all-news"},
    {"source": "매일경제", "url": "https://www.mk.co.kr/rss/50200011/"},
    {"source": "매일경제", "url": "https://www.mk.co.kr/rss/30100041/"},
    {"source": "매일경제", "url": "https://www.mk.co.kr/rss/50100032/"},
]


# ──────────────────────────────────────────────
# 중복 제거 (제목 유사도 기반 Jaccard)
# ──────────────────────────────────────────────
def _tokenize(title: str) -> set:
    """제목을 2글자 이상 토큰 집합으로 변환"""
    title = re.sub(r"[^\w가-힣a-zA-Z0-9]", " ", title)
    return {t for t in title.split() if len(t) >= 2}


def _jaccard(a: str, b: str) -> float:
    sa, sb = _tokenize(a), _tokenize(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def deduplicate(articles: list, threshold: float = 0.5) -> list:
    """URL + 제목 유사도 기반 중복 제거"""
    seen_links: set = set()
    kept: list = []
    kept_titles: list = []

    for art in articles:
        link = art.get("link", "")
        title = art.get("title", "")

        if link and link in seen_links:
            continue

        # 제목 유사도 체크
        is_dup = any(_jaccard(title, t) >= threshold for t in kept_titles)
        if is_dup:
            continue

        if link:
            seen_links.add(link)
        kept.append(art)
        kept_titles.append(title)

    return kept


# ──────────────────────────────────────────────
# 기사 중요도 점수 (키워드 매칭 무관, 순수 뉴스 가치)
# ──────────────────────────────────────────────
def calc_importance(title: str, desc: str = "") -> int:
    """제목과 요약에서 중요도 점수 계산 (최대 15점 캡)"""
    score = 0
    text = title + " " + desc[:100]
    for word, pts in IMPORTANCE_MAP.items():
        if word in text:
            score += pts
    return min(score, 15)


# ──────────────────────────────────────────────
# RSS 수집
# ──────────────────────────────────────────────
def fetch_rss(source: str, url: str) -> list:
    """RSS 한 건을 feedparser로 관대 파싱.
    한경처럼 표준 미준수 XML도 sgmllib 폴백으로 처리되어 lxml invalid token 문제 해소."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"  RSS 다운로드 오류 [{source}]: {e}")
        return []

    feed = feedparser.parse(resp.content)
    # feedparser는 bozo=True여도 entries는 가능한 만큼 채워 반환. 그래도 entries가 비면 사유 출력
    if feed.bozo and not feed.entries:
        reason = getattr(feed, "bozo_exception", "unknown")
        print(f"  RSS 파싱 오류 [{source}]: {reason}")
        return []

    articles = []
    for e in feed.entries:
        title = (e.get("title") or "").strip()
        link  = (e.get("link")  or "").strip()
        raw_desc = e.get("summary") or e.get("description") or ""
        desc  = re.sub(r"<[^>]+>", "", raw_desc).strip()
        desc  = desc[:150] + "..." if len(desc) > 150 else desc
        pub   = (e.get("published") or e.get("updated") or "").strip()

        if not title or not link:
            continue

        articles.append({
            "source": source,
            "title":  title,
            "link":   link,
            "desc":   desc,
            "pub":    pub,
            "via":    "rss",
        })
    return articles


# ──────────────────────────────────────────────
# Naver News API 수집
# ──────────────────────────────────────────────
def fetch_naver_news(query: str, display: int = 10) -> list:
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return []
    try:
        resp = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            headers={
                "X-Naver-Client-Id": NAVER_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
            },
            params={"query": query, "display": display, "sort": "date"},
            timeout=8,
        )
        if resp.status_code != 200:
            return []

        items = resp.json().get("items", [])
        articles = []
        for it in items:
            title = re.sub(r"<[^>]+>", "", it.get("title", "")).strip()
            link  = it.get("link") or it.get("originallink", "")
            desc  = re.sub(r"<[^>]+>", "", it.get("description", "")).strip()
            desc  = desc[:150] + "..." if len(desc) > 150 else desc
            pub   = it.get("pubDate", "")

            # 네이버 블로그/카페는 제외, 뉴스만
            if not title or not link:
                continue
            if "blog.naver" in link or "cafe.naver" in link:
                continue

            articles.append({
                "source": "네이버뉴스",
                "title": title,
                "link": link,
                "desc": desc,
                "pub": pub,
                "via": "naver_api",
            })
        return articles
    except Exception as e:
        print(f"  Naver News API 오류 [{query}]: {e}")
        return []


# ──────────────────────────────────────────────
# 키워드 매칭 (analyzer.py 호환용)
# ──────────────────────────────────────────────
def match_keywords(article: dict, keyword_set: set) -> list:
    title = article.get("title", "")
    desc  = article.get("desc", "")
    matched = []
    for kw in keyword_set:
        if kw in title or kw in desc:
            matched.append(kw)
    return matched


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def run(keywords=None):
    print("=== 경제 뉴스 수집 시작 (RSS + Naver API) ===")

    if keywords is None:
        try:
            with open("keywords_today.json", encoding="utf-8") as f:
                keywords = json.load(f).get("keywords", [])
        except FileNotFoundError:
            keywords = []

    keyword_set = set(keywords)

    # ── 1. RSS 수집 ──
    rss_articles = []
    for feed in RSS_FEEDS:
        items = fetch_rss(feed["source"], feed["url"])
        rss_articles.extend(items)
        label = feed["url"].split("/")[-2] or "main"
        print(f"  RSS {feed['source']} ({label}): {len(items)}건")

    # ── 2. Naver News API 수집 ──
    naver_articles = []
    if NAVER_CLIENT_ID:
        for q in NAVER_SEARCH_QUERIES:
            items = fetch_naver_news(q, display=5)
            naver_articles.extend(items)
        print(f"  Naver News API {len(NAVER_SEARCH_QUERIES)}개 쿼리: 원본 {len(naver_articles)}건")
    else:
        print("  Naver API 키 없음 — RSS만 사용")

    # ── 3. 병합 + 중복 제거 ──
    raw_all = rss_articles + naver_articles
    all_articles = deduplicate(raw_all, threshold=0.5)
    print(f"중복 제거 후 총 {len(all_articles)}건 (원본 {len(raw_all)}건)")

    # ── 4. 중요도 점수 + 키워드 매칭 ──
    keyword_summary = {}
    for art in all_articles:
        imp = calc_importance(art["title"], art.get("desc", ""))
        art["importance"] = imp

        matched = match_keywords(art, keyword_set)
        art["matched_keywords"] = matched

        # analyzer.py 호환: score = importance + 키워드 매칭 보너스
        kw_bonus = sum(3 if kw in art["title"] else 1 for kw in matched)
        art["score"] = imp + kw_bonus

        for kw in matched:
            keyword_summary[kw] = keyword_summary.get(kw, 0) + 1

    # ── 5. 정렬 ──
    # top_news: 중요도 기준 (시황 무관, /news 명령용)
    top_news = sorted(all_articles, key=lambda x: x["importance"], reverse=True)[:15]

    # articles: 키워드 매칭 기사 (analyzer.py 호환)
    matched_articles = [a for a in all_articles if a.get("matched_keywords")]
    matched_articles.sort(key=lambda x: x["score"], reverse=True)

    print(f"중요도 상위 15건 선정 | 키워드 매칭 {len(matched_articles)}건")
    if top_news[:3]:
        print("중요도 상위 3건:")
        for a in top_news[:3]:
            print(f"  [{a['source']}] {a['title'][:50]}... (중요도 {a['importance']})")

    output = {
        "date": datetime.now(KST).strftime("%Y-%m-%d"),
        "collected_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "total_articles": len(all_articles),
        "matched_count": len(matched_articles),
        "top_news": top_news,           # /news 명령용 (중요도 기준, 키워드 무관)
        "articles": matched_articles,   # analyzer.py 호환 (키워드 매칭)
        "top20": matched_articles[:20], # 하위 호환
        "keyword_summary": keyword_summary,
    }

    with open("result_econ_news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("저장 완료 -> result_econ_news.json")
    return output


if __name__ == "__main__":
    run()
