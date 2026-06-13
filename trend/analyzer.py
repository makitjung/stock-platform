# 수집된 데이터를 분석하여 급증 종목을 감지하는 분석 엔진

import json
import os
from datetime import datetime, timedelta


HISTORY_DIR = "history"

# ── 점수 설정 (한 곳에서 튜닝) ─────────────────────────────────
# 각 (임계값, 점수) 튜플. g3/g7은 (증가율 임계 %, 점수).
SCORING = {
    "naver":   {"high": (100, 3), "mid": (50, 2), "low": (20, 1)},
    "youtube": {"high": (1_000_000, 2), "low": (100_000, 1),
                "g3": (100, 2), "g7": (100, 3)},
    # DART는 '중요 공시' 건수 기준이라 작은 수에도 가중 (1건↑ +1, 3건↑ +3)
    "dart":    {"high": (3, 3), "low": (1, 1),
                "g3": (50, 2), "g7": (50, 3)},
    "google":  {"matched": 5},
    "reddit":  {"high": (20, 2), "low": (5, 1),
                "g3": (100, 2), "g7": (100, 3)},
    "econ":    {"title_high": 3, "title": 2, "body": 1, "high_art": 5},
}


def load_json(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_today_snapshot():
    """오늘 수집 결과를 history 폴더에 날짜별로 저장"""
    today = datetime.today().strftime("%Y-%m-%d")
    save_dir = os.path.join(HISTORY_DIR, today)
    os.makedirs(save_dir, exist_ok=True)

    files = [
        "result_naver.json",
        "result_market.json",
        "result_google.json",
        "result_youtube.json",
        "result_reddit.json",
        "result_kind.json",
        "result_sec.json"
    ]

    for fname in files:
        if os.path.exists(fname):
            data = load_json(fname)
            with open(os.path.join(save_dir, fname), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"오늘 스냅샷 저장 완료 -> history/{today}/")


def load_history(filename, days_ago):
    """특정 날짜 전 데이터 로드"""
    target_date = (datetime.today() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    filepath = os.path.join(HISTORY_DIR, target_date, filename)
    return load_json(filepath)


def load_history_flex(filename, min_days, max_days):
    """min_days~max_days 전 범위에서 가장 오래된 사용 가능한 데이터 로드.
    쌓인 히스토리가 적을 때 유연하게 비교 데이터를 찾는다."""
    for days_ago in range(max_days, min_days - 1, -1):
        target_date = (datetime.today() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        filepath = os.path.join(HISTORY_DIR, target_date, filename)
        data = load_json(filepath)
        if data:
            return data
    return {}


def score_keyword(keyword, scores):
    """키워드별 점수 누적"""
    if keyword not in scores:
        scores[keyword] = {
            "keyword": keyword,
            "total_score": 0,
            "signals": [],
            "day1_score": 0,
            "day3_score": 0,
            "day7_score": 0
        }
    return scores[keyword]


def _add(entry, day_key, points, signal=None):
    """점수와 신호를 한 번에 누적."""
    entry["total_score"] += points
    entry[day_key] += points
    if signal:
        entry["signals"].append(signal)


def analyze_naver(scores, naver_data):
    """네이버 데이터랩 분석 - 당일 검색량 증가율(change_rate)만 사용.
    데이터랩 ratio(recent)는 요청마다 30일 최고치 기준으로 재정규화되어
    날짜 간 비교가 흔들리므로, 교차일(3일/7일) 비교는 사용하지 않는다."""
    cfg = SCORING["naver"]
    (t_hi, p_hi), (t_mid, p_mid), (t_low, p_low) = cfg["high"], cfg["mid"], cfg["low"]
    today_map = {item["keyword"]: item.get("change_rate", 0)
                 for item in naver_data.get("datalab", [])}

    for kw, rate in today_map.items():
        entry = score_keyword(kw, scores)
        if rate >= t_hi:
            _add(entry, "day1_score", p_hi, f"네이버 검색 당일 +{rate:.0f}%")
        elif rate >= t_mid:
            _add(entry, "day1_score", p_mid, f"네이버 검색 당일 +{rate:.0f}%")
        elif rate >= t_low:
            _add(entry, "day1_score", p_low)


def analyze_youtube(scores, yt_data, yt_3d, yt_7d):
    """YouTube 조회수 분석"""
    cfg = SCORING["youtube"]
    (t_hi, p_hi), (t_lo, p_lo) = cfg["high"], cfg["low"]
    (g3t, g3p), (g7t, g7p) = cfg["g3"], cfg["g7"]
    today_map = {item["keyword"]: item.get("total_views", 0)
                 for item in yt_data.get("youtube", [])}

    def get_views(data, keyword):
        for item in data.get("youtube", []):
            if item["keyword"] == keyword:
                return item.get("total_views", 0)
        return 0

    for kw, views in today_map.items():
        entry = score_keyword(kw, scores)
        if views >= t_hi:
            _add(entry, "day1_score", p_hi, f"YouTube 조회수 {views:,}")
        elif views >= t_lo:
            _add(entry, "day1_score", p_lo)

        if yt_3d:
            past = get_views(yt_3d, kw)
            if past > 0 and views > past:
                rate = ((views - past) / past) * 100
                if rate >= g3t:
                    _add(entry, "day3_score", g3p, f"YouTube 3일 조회수 +{rate:.0f}%")

        if yt_7d:
            past = get_views(yt_7d, kw)
            if past > 0 and views > past:
                rate = ((views - past) / past) * 100
                if rate >= g7t:
                    _add(entry, "day7_score", g7p, f"YouTube 7일 조회수 +{rate:.0f}%")


def analyze_dart(scores, dart_data, dart_3d, dart_7d):
    """OpenDART 중요 공시 건수 분석 (collector_kind가 루틴 공시를 이미 제외)"""
    cfg = SCORING["dart"]
    (t_hi, p_hi), (t_lo, p_lo) = cfg["high"], cfg["low"]
    (g3t, g3p), (g7t, g7p) = cfg["g3"], cfg["g7"]
    today_map = {item["keyword"]: item.get("disclosure_count", 0)
                 for item in dart_data.get("dart", [])}

    def get_count(data, keyword):
        for item in data.get("dart", []):
            if item["keyword"] == keyword:
                return item.get("disclosure_count", 0)
        return 0

    for kw, count in today_map.items():
        entry = score_keyword(kw, scores)
        if count >= t_hi:
            _add(entry, "day1_score", p_hi, f"중요공시 {count}건")
        elif count >= t_lo:
            _add(entry, "day1_score", p_lo, f"중요공시 {count}건")

        if dart_3d:
            past = get_count(dart_3d, kw)
            if past > 0 and count > past:
                rate = ((count - past) / past) * 100
                if rate >= g3t:
                    _add(entry, "day3_score", g3p, f"중요공시 3일 +{rate:.0f}%")

        if dart_7d:
            past = get_count(dart_7d, kw)
            if past > 0 and count > past:
                rate = ((count - past) / past) * 100
                if rate >= g7t:
                    _add(entry, "day7_score", g7p, f"중요공시 7일 +{rate:.0f}%")


def analyze_google(scores, google_data):
    """Google Trends RSS 급상승 검색어 분석"""
    pts = SCORING["google"]["matched"]
    for item in google_data.get("matched_keywords", []):
        kw = item.get("keyword", "")
        geo = item.get("geo", "")
        entry = score_keyword(kw, scores)
        _add(entry, "day1_score", pts, f"Google 급상승 검색어 등장 ({geo})")


def analyze_reddit(scores, reddit_data, reddit_3d, reddit_7d):
    """Reddit 게시물 분석"""
    cfg = SCORING["reddit"]
    (t_hi, p_hi), (t_lo, p_lo) = cfg["high"], cfg["low"]
    (g3t, g3p), (g7t, g7p) = cfg["g3"], cfg["g7"]
    today_map = {item["keyword"]: item.get("post_count", 0)
                 for item in reddit_data.get("reddit", [])}

    def get_posts(data, keyword):
        for item in data.get("reddit", []):
            if item["keyword"] == keyword:
                return item.get("post_count", 0)
        return 0

    for kw, count in today_map.items():
        entry = score_keyword(kw, scores)
        if count >= t_hi:
            _add(entry, "day1_score", p_hi, f"Reddit {count}건")
        elif count >= t_lo:
            _add(entry, "day1_score", p_lo)

        if reddit_3d:
            past = get_posts(reddit_3d, kw)
            if past > 0 and count > past:
                rate = ((count - past) / past) * 100
                if rate >= g3t:
                    _add(entry, "day3_score", g3p, f"Reddit 3일 +{rate:.0f}%")

        if reddit_7d:
            past = get_posts(reddit_7d, kw)
            if past > 0 and count > past:
                rate = ((count - past) / past) * 100
                if rate >= g7t:
                    _add(entry, "day7_score", g7p, f"Reddit 7일 +{rate:.0f}%")


def analyze_econ_news(scores, econ_data):
    """한경·매경 기사 매칭 분석 — 제목 언급(중요기사면 +) / 본문 언급"""
    cfg = SCORING["econ"]
    for article in econ_data.get("articles", []):
        art_score = article.get("score", 0)
        source    = article.get("source", "")
        title     = article.get("title", "")

        for kw in article.get("matched_keywords", []):
            entry = score_keyword(kw, scores)
            if kw in title:
                bonus = cfg["title_high"] if art_score >= cfg["high_art"] else cfg["title"]
                _add(entry, "day1_score", bonus, f"{source} 헤드라인 언급")
            else:
                _add(entry, "day1_score", cfg["body"], f"{source} 기사 언급")

def _load_stock_names() -> set:
    """거래소 상장 종목명 집합 로드 (is_stock 판별용, 테마 키워드 제외)"""
    try:
        with open("krx_stock_names.json", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("names", []))
    except Exception:
        return set()


def _load_codes() -> dict:
    """종목명 -> 코드 맵 로드 (finance.naver 종목 페이지 링크용)"""
    try:
        with open("krx_codes.json", encoding="utf-8") as f:
            return json.load(f).get("codes", {})
    except Exception:
        return {}


def _compute_streaks(top50: list):
    """각 종목의 연속 신호일(streak_days)을 history 분석 스냅샷으로 계산.
    달력일이 아니라 '존재하는 과거 스냅샷'을 거슬러 세어 주말·휴장 공백을 건너뛴다.
    오늘(top50에 점수>0으로 포함)이 1일째이며, 직전 스냅샷부터 연속으로
    점수>0이면 +1, 끊기면 중단."""
    today = datetime.today().strftime("%Y-%m-%d")

    # 과거 스냅샷 날짜(오늘 제외)를 최신순으로 수집
    try:
        past_dates = sorted(
            (d for d in os.listdir(HISTORY_DIR)
             if d < today and os.path.isfile(os.path.join(HISTORY_DIR, d, "result_analysis.json"))),
            reverse=True,
        )
    except FileNotFoundError:
        past_dates = []

    # 날짜별 '점수>0 키워드 집합' 캐시
    scored_sets = []
    for d in past_dates:
        data = load_json(os.path.join(HISTORY_DIR, d, "result_analysis.json"))
        scored_sets.append({
            it["keyword"] for it in data.get("top50", [])
            if it.get("total_score", 0) > 0
        })

    for item in top50:
        kw = item["keyword"]
        streak = 1  # 오늘
        for past_set in scored_sets:
            if kw in past_set:
                streak += 1
            else:
                break
        item["streak_days"] = streak


def _save_date_analysis(output: dict):
    """날짜별 분석 결과를 history에 저장하고 result_dates.json 갱신"""
    date = output["date"]
    date_dir = os.path.join(HISTORY_DIR, date)
    os.makedirs(date_dir, exist_ok=True)

    analysis_path = os.path.join(date_dir, "result_analysis.json")
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    dates_path = "result_dates.json"
    try:
        with open(dates_path, encoding="utf-8") as f:
            dates_data = json.load(f)
    except Exception:
        dates_data = {"dates": []}

    dates = dates_data.get("dates", [])
    if date not in dates:
        dates.append(date)
    dates = sorted(set(dates), reverse=True)

    # 시장 데이터 공백 여부 확인 (날짜 선택기에서 표시용)
    empty_market: list = dates_data.get("empty_market", [])
    market_path = os.path.join(HISTORY_DIR, date, "result_market.json")
    market_is_empty = True
    try:
        with open(market_path, encoding="utf-8") as f:
            mkt = json.load(f)
        def _has_data(sec):
            return any(len(mkt.get(sec, {}).get(cat, [])) > 0
                       for cat in ["상한가", "하한가", "급등", "급락"])
        market_is_empty = not (_has_data("kospi") or _has_data("kosdaq"))
    except Exception:
        pass

    if market_is_empty and date not in empty_market:
        empty_market.append(date)
    elif not market_is_empty and date in empty_market:
        empty_market.remove(date)

    with open(dates_path, "w", encoding="utf-8") as f:
        json.dump({"dates": dates, "empty_market": empty_market}, f, ensure_ascii=False)

    print(f"날짜별 분석 저장 -> history/{date}/result_analysis.json ({len(dates)}일 누적)")


def run():
    print("=== 분석 시작 ===")

    save_today_snapshot()

    naver = load_json("result_naver.json")
    google = load_json("result_google.json")
    youtube = load_json("result_youtube.json")
    reddit = load_json("result_reddit.json")
    dart = load_json("result_kind.json")
    econ_news = load_json("result_econ_news.json")

    # 3일 비교: 2~4일 전 범위에서 가장 오래된 데이터 (히스토리 2일치 이상이면 활성화)
    # 7일 비교: 5~10일 전 범위에서 가장 오래된 데이터 (히스토리 5일치 이상이면 활성화)
    naver_3d = load_history_flex("result_naver.json", 2, 4)
    naver_7d = load_history_flex("result_naver.json", 5, 10)
    yt_3d = load_history_flex("result_youtube.json", 2, 4)
    yt_7d = load_history_flex("result_youtube.json", 5, 10)
    dart_3d = load_history_flex("result_kind.json", 2, 4)
    dart_7d = load_history_flex("result_kind.json", 5, 10)
    reddit_3d = load_history_flex("result_reddit.json", 2, 4)
    reddit_7d = load_history_flex("result_reddit.json", 5, 10)

    has_3d = bool(naver_3d or yt_3d)
    has_7d = bool(naver_7d or yt_7d)

    if has_7d:
        print("비교 모드: 당일 + 3일 + 7일 비교 활성화")
    elif has_3d:
        print("비교 모드: 당일 + 3일 비교 활성화")
    else:
        print("당일 모드: 오늘 데이터만으로 분석 (3일/7일 누적 후 비교 활성화)")

    scores = {}

    analyze_naver(scores, naver)
    analyze_youtube(scores, youtube, yt_3d, yt_7d)
    analyze_dart(scores, dart, dart_3d, dart_7d)
    analyze_google(scores, google)
    analyze_reddit(scores, reddit, reddit_3d, reddit_7d)
    analyze_econ_news(scores, econ_news)

    ranked = sorted(scores.values(), key=lambda x: x["total_score"], reverse=True)
    top50 = [r for r in ranked if r["total_score"] > 0][:50]

    stock_names = _load_stock_names()
    codes = _load_codes()
    for item in top50:
        item["is_stock"] = item["keyword"] in stock_names
        code = codes.get(item["keyword"])
        if code:
            item["code"] = code  # 대시보드 finance.naver 종목 페이지 링크용

    _compute_streaks(top50)

    output = {
        "date": datetime.today().strftime("%Y-%m-%d"),
        "mode": "7일비교" if has_7d else ("3일비교" if has_3d else "당일"),
        "total_analyzed": len(scores),
        "top50": top50
    }

    with open("result_analysis.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    _save_date_analysis(output)

    print(f"분석 완료. 신호 감지 {len(top50)}개 -> result_analysis.json")
    if top50:
        print("\n상위 10개 종목:")
        for i, item in enumerate(top50[:10], 1):
            print(f"  {i}. {item['keyword']} | 점수 {item['total_score']} | {', '.join(item['signals'][:2])}")

    return output


if __name__ == "__main__":
    run()
