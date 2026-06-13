# 백그라운드 스크립트(메인/스레드) 크래시를 마지막 traceback 일부와 함께 텔레그램으로 보내는 모듈

import sys
import os
import traceback
import threading
from datetime import datetime

# common.telegram은 import 시점에 .env를 읽어 들이므로 안전하게 lazy import 사용
def _safe_send(text: str) -> None:
    try:
        from common.telegram import send_message
        send_message(text, tag="CRASH")
    except Exception as e:
        # 크래시 알림 자체가 실패해도 절대 추가 예외를 던지지 않는다
        try:
            print(f"[crash_notify] 알림 전송 실패: {e}", file=sys.stderr)
        except Exception:
            pass


def _format_tb(exc_type, exc_value, exc_tb, tag: str = "", extra: str = "") -> str:
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    # 텔레그램 메시지 길이 한계를 고려해 마지막 1500자만 남김
    tail = tb_text[-1500:]
    header_parts = ["💥 <b>크래시 발생</b>"]
    if tag:
        header_parts.append(f"[{tag}]")
    header_parts.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    head = " ".join(header_parts)
    body = extra + ("\n" if extra else "") + f"<pre>{_escape(tail)}</pre>"
    return f"{head}\n{body}"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def install_excepthook(tag: str = "") -> None:
    """메인 스레드의 미처리 예외를 텔레그램으로 전송한 뒤 기본 동작(stderr 출력) 수행."""
    if not tag:
        tag = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else "python"
    original = sys.excepthook

    def hook(exc_type, exc_value, exc_tb):
        # KeyboardInterrupt 같은 정상 종료 시그널은 알림 제외
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            return original(exc_type, exc_value, exc_tb)
        _safe_send(_format_tb(exc_type, exc_value, exc_tb, tag=tag))
        return original(exc_type, exc_value, exc_tb)

    sys.excepthook = hook

    # 스레드 미처리 예외도 동일하게 처리
    original_thread = threading.excepthook

    def thread_hook(args):
        if issubclass(args.exc_type, (KeyboardInterrupt, SystemExit)):
            return original_thread(args)
        _safe_send(_format_tb(args.exc_type, args.exc_value, args.exc_traceback, tag=f"{tag}/thread"))
        return original_thread(args)

    threading.excepthook = thread_hook


def report_crash(tag: str = "", message: str = "") -> None:
    """except 블록 안에서 호출. 현재 sys.exc_info()를 텔레그램으로 보낸다."""
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_type is None:
        return
    _safe_send(_format_tb(exc_type, exc_value, exc_tb, tag=tag, extra=_escape(message) if message else ""))
