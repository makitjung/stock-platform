# common.alarm_engine 룰/중복차단/점수 산정 동작을 검증하는 단위 테스트

import os
import sys
import unittest

PLATFORM_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PLATFORM_DIR)

from common import alarm_engine


def _state():
    """매 테스트마다 깨끗한 state dict 반환."""
    return alarm_engine._empty_state("TEST")


class TestPriceSpike(unittest.TestCase):
    def test_threshold_and_dedup(self):
        stocks = [
            {"name": "A", "ticker": "AAA", "market": "KR", "change_rate":  6.0},
            {"name": "B", "ticker": "BBB", "market": "US", "change_rate": -4.9},  # 미만 → 통과 X
            {"name": "C", "ticker": "CCC", "market": "KR", "change_rate": None},  # None → 통과 X
        ]
        state = _state()
        first = alarm_engine.check_price_spike(stocks, state)
        self.assertEqual(len(first), 1)
        self.assertIn("AAA", first[0])

        # 같은 state로 재호출 시 중복 차단
        second = alarm_engine.check_price_spike(stocks, state)
        self.assertEqual(second, [])

    def test_negative_spike(self):
        stocks = [{"name": "X", "ticker": "X", "market": "KR", "change_rate": -7.5}]
        lines = alarm_engine.check_price_spike(stocks, _state())
        self.assertEqual(len(lines), 1)
        self.assertIn("▼7.50%", lines[0])


class TestVolumeSpike(unittest.TestCase):
    def test_multiplier_and_dedup(self):
        stocks = [
            {"name": "A", "ticker": "AAA", "market": "KR", "volume": 9_000_000},  # 3x
            {"name": "B", "ticker": "BBB", "market": "US", "volume": 5_999_999},  # 1.99x → X
            {"name": "C", "ticker": "CCC", "market": "KR", "volume": None},        # None → X
            {"name": "D", "ticker": "DDD", "market": "US", "volume": 100_000_000}, # 10x
        ]
        baseline = {"AAA": 3_000_000, "BBB": 3_000_000, "CCC": 1_000, "DDD": 10_000_000}
        state = _state()
        first = alarm_engine.check_volume_spike(stocks, baseline, state)
        self.assertEqual(len(first), 2)
        tickers_fired = {ln.split("(")[1].split(")")[0] for ln in first}
        self.assertEqual(tickers_fired, {"AAA", "DDD"})

        # 중복 차단
        again = alarm_engine.check_volume_spike(stocks, baseline, state)
        self.assertEqual(again, [])

    def test_missing_baseline_skipped(self):
        stocks = [{"name": "Z", "ticker": "ZZZ", "market": "KR", "volume": 999_999_999}]
        lines = alarm_engine.check_volume_spike(stocks, {}, _state())  # baseline 없음
        self.assertEqual(lines, [])

    def test_zero_baseline_skipped(self):
        stocks = [{"name": "Z", "ticker": "ZZZ", "market": "KR", "volume": 100}]
        lines = alarm_engine.check_volume_spike(stocks, {"ZZZ": 0}, _state())
        self.assertEqual(lines, [])


class TestNewsAlerts(unittest.TestCase):
    def test_score_threshold(self):
        news = {
            "대륙제관": [
                {"title": "대륙제관 단일판매·공급계약 체결",       "url": "u1"},  # 단일판매 5 + 공급계약 7 = 12 ≥10
                {"title": "그냥 평범한 뉴스",                      "url": "u2"},  # 0
                {"title": "대륙제관 FDA 임상 승인",                "url": "u3"},  # FDA 7 + 임상 5 + 승인 5 = 17
            ],
            "비종목": [],   # 빈 items 통과 X
        }
        state = _state()
        first = alarm_engine.check_news_alerts(news, state)
        self.assertEqual(len(first), 2)
        # 중복 차단
        self.assertEqual(alarm_engine.check_news_alerts(news, state), [])

    def test_score_function(self):
        self.assertEqual(alarm_engine.score_news_title(""), 0)
        self.assertEqual(alarm_engine.score_news_title("평범한 제목"), 0)
        # 단일판매(5) + 공급계약(7) = 12
        self.assertEqual(alarm_engine.score_news_title("단일판매 공급계약"), 12)


class TestStateLifecycle(unittest.TestCase):
    def test_empty_state_shape(self):
        s = alarm_engine._empty_state("2026-01-01")
        self.assertEqual(s["date"], "2026-01-01")
        self.assertEqual(s["price_fired"], [])
        self.assertEqual(s["volume_fired"], [])
        self.assertEqual(s["news_fired"], [])


if __name__ == "__main__":
    unittest.main()
