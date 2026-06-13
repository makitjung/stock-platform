# analyzer 점수 계산·연속신호(streak) 로직 단위 테스트

import os
import sys
import json
import tempfile
import unittest

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)

import analyzer


class TestNaverScoring(unittest.TestCase):
    def test_thresholds(self):
        scores = {}
        analyzer.analyze_naver(scores, {"datalab": [
            {"keyword": "A", "change_rate": 120},  # >=100 -> 3
            {"keyword": "B", "change_rate": 60},   # >=50  -> 2
            {"keyword": "C", "change_rate": 25},   # >=20  -> 1
            {"keyword": "D", "change_rate": 5},    # <20   -> 0
        ]})
        self.assertEqual(scores["A"]["total_score"], 3)
        self.assertEqual(scores["B"]["total_score"], 2)
        self.assertEqual(scores["C"]["total_score"], 1)
        self.assertEqual(scores["D"]["total_score"], 0)  # 항목은 생성되나 점수 0

    def test_zero_has_no_points(self):
        scores = {}
        analyzer.analyze_naver(scores, {"datalab": [{"keyword": "D", "change_rate": 5}]})
        self.assertEqual(scores["D"]["total_score"], 0)


class TestYoutubeScoring(unittest.TestCase):
    def test_day1_and_growth(self):
        scores = {}
        analyzer.analyze_youtube(
            scores,
            {"youtube": [{"keyword": "Y", "total_views": 1_200_000}]},  # >=1M -> 2
            {"youtube": [{"keyword": "Y", "total_views": 500_000}]},    # 3d +140% -> 2
            {},
        )
        self.assertEqual(scores["Y"]["total_score"], 4)
        self.assertEqual(scores["Y"]["day3_score"], 2)


class TestDartMaterialScoring(unittest.TestCase):
    def test_material_thresholds_and_label(self):
        scores = {}
        analyzer.analyze_dart(scores, {"dart": [
            {"keyword": "D3", "disclosure_count": 3},  # >=3 -> 3
            {"keyword": "D1", "disclosure_count": 1},  # >=1 -> 1
            {"keyword": "D0", "disclosure_count": 0},  # 0   -> 0
        ]}, {}, {})
        self.assertEqual(scores["D3"]["total_score"], 3)
        self.assertEqual(scores["D1"]["total_score"], 1)
        self.assertEqual(scores["D0"]["total_score"], 0)
        # 신호 문구가 '중요공시'로 표기되는지
        self.assertTrue(any("중요공시" in s for s in scores["D3"]["signals"]))


class TestGoogleReddit(unittest.TestCase):
    def test_google_matched(self):
        scores = {}
        analyzer.analyze_google(scores, {"matched_keywords": [{"keyword": "G", "geo": "KR"}]})
        self.assertEqual(scores["G"]["total_score"], 5)

    def test_reddit_thresholds(self):
        scores = {}
        analyzer.analyze_reddit(scores, {"reddit": [
            {"keyword": "R20", "post_count": 20},
            {"keyword": "R5", "post_count": 5},
            {"keyword": "R2", "post_count": 2},
        ]}, {}, {})
        self.assertEqual(scores["R20"]["total_score"], 2)
        self.assertEqual(scores["R5"]["total_score"], 1)
        self.assertEqual(scores["R2"]["total_score"], 0)


class TestEconNews(unittest.TestCase):
    def test_title_vs_body(self):
        scores = {}
        analyzer.analyze_econ_news(scores, {"articles": [
            {"score": 6, "source": "한경", "title": "AABB 급등", "matched_keywords": ["AABB"]},  # 제목+중요 -> 3
            {"score": 2, "source": "매경", "title": "CCDD 신규", "matched_keywords": ["CCDD"]},  # 제목 -> 2
            {"score": 9, "source": "한경", "title": "무관", "matched_keywords": ["EEFF"]},        # 본문 -> 1
        ]})
        self.assertEqual(scores["AABB"]["total_score"], 3)
        self.assertEqual(scores["CCDD"]["total_score"], 2)
        self.assertEqual(scores["EEFF"]["total_score"], 1)


class TestStreak(unittest.TestCase):
    def test_streak_counts_consecutive_snapshots(self):
        tmp = tempfile.mkdtemp()
        # 과거 스냅샷 두 개 (오늘보다 이전 날짜)
        def write(date, kws):
            d = os.path.join(tmp, date)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "result_analysis.json"), "w", encoding="utf-8") as f:
                json.dump({"top50": [{"keyword": k, "total_score": 5} for k in kws]}, f)
        write("2020-01-01", ["X", "Y"])
        write("2020-01-02", ["X"])  # 가장 최근 과거 스냅샷
        orig = analyzer.HISTORY_DIR
        analyzer.HISTORY_DIR = tmp
        try:
            top = [{"keyword": "X"}, {"keyword": "Y"}, {"keyword": "Z"}]
            analyzer._compute_streaks(top)
        finally:
            analyzer.HISTORY_DIR = orig
        by = {t["keyword"]: t["streak_days"] for t in top}
        self.assertEqual(by["X"], 3)  # 오늘 + 01-02 + 01-01 연속
        self.assertEqual(by["Y"], 1)  # 01-02에 없어 연속 끊김 -> 오늘만
        self.assertEqual(by["Z"], 1)  # 과거 전무 -> 오늘만


if __name__ == "__main__":
    unittest.main()
