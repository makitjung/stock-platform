# 뉴스 제목 유사도 기반 중복 제거 모듈

import re
from difflib import SequenceMatcher


def normalize(title):
    """HTML 태그 제거 및 공백 정규화."""
    title = re.sub(r"<[^>]+>", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def deduplicate(news_list, threshold=0.70):
    """같은 날짜 내 제목 유사도 threshold 이상이면 중복 제거."""
    seen = []
    result = []
    for item in news_list:
        title = normalize(item.get("title", ""))
        date  = item.get("date", "")
        is_dup = False
        for s_title, s_date in seen:
            if date and date == s_date and similarity(title, s_title) >= threshold:
                is_dup = True
                break
        if not is_dup:
            seen.append((title, date))
            result.append(item)
    return result


def deduplicate_across_stocks(all_news, threshold=0.75):
    """종목 간 중복 뉴스를 한 종목에만 남기는 dedup."""
    global_seen = []
    deduped = {}
    for stock_name, news_items in all_news.items():
        deduped[stock_name] = []
        for item in news_items:
            title = normalize(item.get("title", ""))
            date  = item.get("date", "")
            is_dup = False
            for s_title, s_date, _ in global_seen:
                if date and date == s_date and similarity(title, s_title) >= threshold:
                    is_dup = True
                    break
            if not is_dup:
                global_seen.append((title, date, stock_name))
                deduped[stock_name].append(item)
    return deduped
