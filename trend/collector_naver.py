# 네이버 데이터랩 및 뉴스 API로 국내 종목 검색 트렌드를 수집하는 모듈

import json
import time
from datetime import datetime

from common.api_naver import datalab_trend as get_datalab_trend, news_count as get_news_count


def run(keywords=None):
    print("=== 네이버 트렌드 수집 시작 ===")

    if keywords is None:
        try:
            with open("keywords_today.json", "r", encoding="utf-8") as f:
                keywords = json.load(f).get("keywords", [])
        except FileNotFoundError:
            print("keywords_today.json 없음.")
            return {}

    print(f"전체 키워드 {len(keywords)}개")

    # 데이터랩: 상위 100개만 (API 호출 20회로 감소)
    datalab_target = keywords[:100]
    datalab_results = []
    for i in range(0, len(datalab_target), 5):
        batch = datalab_target[i:i+5]
        datalab_results.extend(get_datalab_trend(batch))
        time.sleep(0.3)
        if i % 50 == 0 and i > 0:
            print(f"데이터랩 진행중... {i}/{len(datalab_target)}")
    print(f"데이터랩 수집 완료. {len(datalab_results)}개")

    # 증가율 상위 50개만 뉴스 확인
    datalab_results.sort(key=lambda x: x["change_rate"], reverse=True)
    news_results = []
    for item in datalab_results[:50]:
        news_results.append(get_news_count(item["keyword"]))
        time.sleep(0.1)
    print(f"뉴스 수집 완료. {len(news_results)}개")

    output = {
        "date": datetime.today().strftime("%Y-%m-%d"),
        "collected_at": datetime.today().strftime("%Y-%m-%d %H:%M"),
        "datalab": datalab_results,
        "news": news_results
    }
    with open("result_naver.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("저장 완료 -> result_naver.json")
    return output


if __name__ == "__main__":
    run()
