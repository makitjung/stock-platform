# backtest 수익률 계산·집계 로직 단위 테스트

import os
import sys
import unittest
import datetime
import pandas as pd

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)

import backtest


def _series(prices):
    """연속 거래일 종가 시계열 생성."""
    idx = pd.to_datetime([f"2026-05-{d:02d}" for d in range(1, 1 + len(prices))])
    return pd.DataFrame({"Close": prices}, index=idx)


class TestForwardReturn(unittest.TestCase):
    def test_positive_return(self):
        s = _series([100, 110, 120])  # 05-01..05-03
        # 05-01 기준 +1거래일 -> 110 (=+10%), +2거래일 -> 120 (=+20%)
        self.assertEqual(backtest._forward_return(s, "2026-05-01", 1), 10.0)
        self.assertEqual(backtest._forward_return(s, "2026-05-01", 2), 20.0)

    def test_insufficient_future_returns_none(self):
        s = _series([100, 110])
        self.assertIsNone(backtest._forward_return(s, "2026-05-02", 1))


class TestSummarize(unittest.TestCase):
    def test_win_rate_and_avg(self):
        out = backtest._summarize([10.0, -5.0, 20.0, -2.0])
        self.assertEqual(out["sample"], 4)
        self.assertEqual(out["win_rate"], 50.0)        # 2/4 양수
        self.assertEqual(out["avg_return"], 5.75)      # (10-5+20-2)/4
        self.assertEqual(out["avg_win"], 15.0)         # (10+20)/2

    def test_empty(self):
        out = backtest._summarize([])
        self.assertEqual(out["sample"], 0)
        self.assertIsNone(out["win_rate"])


if __name__ == "__main__":
    unittest.main()
