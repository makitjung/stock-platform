import json, os
from datetime import datetime

data = [
    {"keyword": "한온시스템", "recent": 39, "previous": 6, "change_rate": 550, "source": "google_trends_chrome"},
    {"keyword": "대한광통신", "recent": 23, "previous": 8, "change_rate": 188, "source": "google_trends_chrome"},
    {"keyword": "코스모로보틱스", "recent": 32, "previous": 1, "change_rate": 3100, "source": "google_trends_chrome"},
    {"keyword": "삼성전자", "recent": 50, "previous": 60, "change_rate": -17, "source": "google_trends_chrome"},
    {"keyword": "빛과전자", "recent": 19, "previous": 1, "change_rate": 1800, "source": "google_trends_chrome"},
    {"keyword": "광전자", "recent": 24, "previous": 2, "change_rate": 1100, "source": "google_trends_chrome"},
    {"keyword": "진원생명과학", "recent": 0, "previous": 4, "change_rate": -100, "source": "google_trends_chrome"},
    {"keyword": "SK증권", "recent": 22, "previous": 41, "change_rate": -46, "source": "google_trends_chrome"},
    {"keyword": "HB테크놀러지", "recent": 9, "previous": 0, "change_rate": 0, "source": "google_trends_chrome"},
    {"keyword": "아주IB투자", "recent": 4, "previous": 0, "change_rate": 0, "source": "google_trends_chrome"},
    {"keyword": "이랜시스", "recent": 6, "previous": 0, "change_rate": 0, "source": "google_trends_chrome"},
    {"keyword": "계양전기", "recent": 10, "previous": 0, "change_rate": 0, "source": "google_trends_chrome"},
    {"keyword": "기가레인", "recent": 10, "previous": 0, "change_rate": 0, "source": "google_trends_chrome"},
    {"keyword": "선도전기", "recent": 18, "previous": 0, "change_rate": 0, "source": "google_trends_chrome"},
    {"keyword": "드림시큐리티", "recent": 7, "previous": 0, "change_rate": 0, "source": "google_trends_chrome"},
    {"keyword": "KBI메탈", "recent": 5, "previous": 0, "change_rate": 0, "source": "google_trends_chrome"},
]

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result_google.json")

existing = {}
if os.path.exists(path):
    existing = json.loads(open(path, encoding="utf-8").read())

existing["keyword_trends"] = data
existing["date"] = datetime.today().strftime("%Y-%m-%d")
existing["source"] = "google_trends_chrome"

open(path, "w", encoding="utf-8").write(json.dumps(existing, ensure_ascii=False, indent=2))
print("저장 완료. 수집 종목:", len(data))
