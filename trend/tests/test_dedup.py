# common.dedup 중복 제거 로직 단위 테스트

import os
import sys
import unittest

PLATFORM_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PLATFORM_DIR)

from common.dedup import normalize, deduplicate, deduplicate_across_stocks


class TestNormalize(unittest.TestCase):
    def test_strips_html_and_spaces(self):
        self.assertEqual(normalize("<b>포스코</b>   흑자"), "포스코 흑자")


class TestDeduplicate(unittest.TestCase):
    def test_same_day_similar_titles_merge(self):
        items = [
            {"title": "<b>포스코 흑자 전환</b>", "date": "2026-05-22"},
            {"title": "포스코 흑자 전환", "date": "2026-05-22"},   # 유사 -> 제거
            {"title": "네이버 신규 서비스", "date": "2026-05-22"},
        ]
        self.assertEqual(len(deduplicate(items)), 2)

    def test_different_dates_not_merged(self):
        items = [
            {"title": "동일 제목", "date": "2026-05-21"},
            {"title": "동일 제목", "date": "2026-05-22"},  # 날짜 다르면 유지
        ]
        self.assertEqual(len(deduplicate(items)), 2)


class TestDeduplicateAcrossStocks(unittest.TestCase):
    def test_cross_stock_dedup(self):
        all_news = {
            "포스코퓨처엠": [{"title": "포스코그룹 대규모 투자 발표", "date": "2026-05-22"}],
            "필에너지":     [{"title": "포스코그룹 대규모 투자 발표", "date": "2026-05-22"}],  # 중복 -> 한쪽만
        }
        out = deduplicate_across_stocks(all_news)
        total = sum(len(v) for v in out.values())
        self.assertEqual(total, 1)


if __name__ == "__main__":
    unittest.main()
