# YouTube Data API v3로 종목 키워드 영상 수 및 조회수 급증을 감지하는 모듈
# NOTE: 현재 orchestrator AGENTS_FULL에서 제외 (quota 부담 + 종목명 노이즈 대비 신호 가치 낮음).
#       발굴 신호로 재활성화하려면 orchestrator.AGENTS_FULL에 다시 추가하면 된다.

import json
import time
from datetime import datetime, timedelta
from googleapiclient.discovery import build

from common.config import YOUTUBE_API_KEY


def search_keyword(youtube, keyword, days=7):
    """특정 키워드의 최근 영상 수와 총 조회수 수집"""
    published_after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        response = youtube.search().list(
            q=keyword,
            part="snippet",
            type="video",
            publishedAfter=published_after,
            maxResults=50,
            relevanceLanguage="ko",
            order="viewCount"
        ).execute()

        video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
        if not video_ids:
            return {"keyword": keyword, "video_count": 0, "total_views": 0, "source": "youtube"}

        stats = youtube.videos().list(
            part="statistics",
            id=",".join(video_ids)
        ).execute()

        total_views = 0
        for item in stats.get("items", []):
            views = item.get("statistics", {}).get("viewCount", 0)
            total_views += int(views)

        return {
            "keyword": keyword,
            "video_count": len(video_ids),
            "total_views": total_views,
            "source": "youtube"
        }

    except Exception as e:
        print(f"YouTube 오류 ({keyword}): {e}")
        return {"keyword": keyword, "video_count": 0, "total_views": 0, "source": "youtube"}


def run(keywords=None):
    print("=== YouTube 트렌드 수집 시작 ===")

    if keywords is None:
        try:
            with open("keywords_today.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            keywords = data.get("keywords", [])
        except FileNotFoundError:
            print("keywords_today.json 없음. krx_symbols.py를 먼저 실행하세요.")
            return {}

    # YouTube API는 하루 10,000 유닛. 검색 1회=100유닛, 영상통계=1유닛
    # 상위 50개 키워드만 처리 (50회 검색 = 5,000유닛 소비)
    keywords = keywords[:50]
    print(f"대상 키워드 {len(keywords)}개 (상위 50개)")

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    results = []

    for i, kw in enumerate(keywords):
        result = search_keyword(youtube, kw)
        results.append(result)
        time.sleep(0.5)
        if (i + 1) % 10 == 0:
            print(f"진행중... {i+1}/{len(keywords)}")

    results.sort(key=lambda x: x["total_views"], reverse=True)

    output = {
        "date": datetime.today().strftime("%Y-%m-%d"),
        "youtube": results
    }

    with open("result_youtube.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"수집 완료. {len(results)}개 저장 -> result_youtube.json")
    return output


if __name__ == "__main__":
    run()
