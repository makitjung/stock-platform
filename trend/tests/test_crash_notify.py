# common.crash_notify의 포맷팅/이스케이프/excepthook 설치 동작을 검증하는 단위 테스트

import os
import sys
import unittest
from unittest import mock

PLATFORM_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PLATFORM_DIR)

from common import crash_notify


class TestEscape(unittest.TestCase):
    def test_html_special_chars(self):
        self.assertEqual(crash_notify._escape("<b>&hi</b>"), "&lt;b&gt;&amp;hi&lt;/b&gt;")

    def test_no_change(self):
        self.assertEqual(crash_notify._escape("plain text"), "plain text")


class TestFormatTraceback(unittest.TestCase):
    def test_tag_and_extra_included(self):
        try:
            raise ValueError("의도된 오류")
        except ValueError:
            t, v, tb = sys.exc_info()
            text = crash_notify._format_tb(t, v, tb, tag="UNIT", extra="추가 메시지")
        self.assertIn("UNIT", text)
        self.assertIn("추가 메시지", text)
        self.assertIn("ValueError", text)
        self.assertIn("의도된 오류", text)

    def test_traceback_truncated_to_1500_chars(self):
        # 인위적으로 깊은 traceback 만들어서 길이 제한 확인
        def deep(n):
            if n == 0:
                raise RuntimeError("x" * 5000)
            return deep(n - 1)
        try:
            deep(50)
        except RuntimeError:
            t, v, tb = sys.exc_info()
            text = crash_notify._format_tb(t, v, tb)
        # tail은 1500자 이내 + 헤더 + <pre></pre> 태그가 붙음
        # body 내부 pre 길이가 1500 이하면 OK
        import re
        m = re.search(r"<pre>(.*?)</pre>", text, re.S)
        self.assertIsNotNone(m)
        self.assertLessEqual(len(m.group(1)), 1500)


class TestSafeSend(unittest.TestCase):
    def test_send_failure_is_swallowed(self):
        """텔레그램 send_message가 raise해도 _safe_send는 예외를 던지지 않아야 한다."""
        # common.telegram.send_message를 raise하도록 패치
        with mock.patch("common.telegram.send_message", side_effect=RuntimeError("boom")):
            # 예외 없이 반환해야 한다
            try:
                crash_notify._safe_send("test")
            except Exception as e:
                self.fail(f"_safe_send raised {e}")

    def test_send_success_calls_tag_crash(self):
        with mock.patch("common.telegram.send_message") as m:
            crash_notify._safe_send("hello")
            m.assert_called_once()
            args, kwargs = m.call_args
            self.assertEqual(kwargs.get("tag"), "CRASH")


class TestInstallExcepthook(unittest.TestCase):
    def test_hook_runs_safe_send_on_uncaught(self):
        """install_excepthook 후 강제 발생한 예외가 _safe_send를 트리거하는지 확인."""
        sent = []
        with mock.patch.object(crash_notify, "_safe_send", side_effect=lambda t: sent.append(t)):
            # 원본 sys.excepthook을 보존했다가 복구
            original = sys.excepthook
            try:
                crash_notify.install_excepthook("TESTHOOK")
                try:
                    raise IndexError("hook me")
                except IndexError:
                    t, v, tb = sys.exc_info()
                    # 직접 hook 호출(미처리 시뮬레이션)
                    sys.excepthook(t, v, tb)
            finally:
                sys.excepthook = original

        self.assertEqual(len(sent), 1)
        self.assertIn("TESTHOOK", sent[0])
        self.assertIn("IndexError", sent[0])

    def test_keyboard_interrupt_not_reported(self):
        sent = []
        with mock.patch.object(crash_notify, "_safe_send", side_effect=lambda t: sent.append(t)):
            original = sys.excepthook
            try:
                crash_notify.install_excepthook("TESTHOOK")
                try:
                    raise KeyboardInterrupt()
                except KeyboardInterrupt:
                    t, v, tb = sys.exc_info()
                    sys.excepthook(t, v, tb)
            finally:
                sys.excepthook = original
        self.assertEqual(sent, [])


if __name__ == "__main__":
    unittest.main()
