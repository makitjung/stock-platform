# 텔레그램 메시지 및 파일 전송을 [TREND]/[NEWS] 태그로 통합하는 공용 모듈

import requests

from common.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

API_BASE = "https://api.telegram.org/bot"


def _prefix(text, tag):
    if not tag:
        return text
    return f"[{tag.upper()}] {text}"


def send_message(text, tag=""):
    """텔레그램 메시지 전송. tag가 주어지면 본문 앞에 대괄호로 붙임."""
    url = f"{API_BASE}{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id":                  TELEGRAM_CHAT_ID,
        "text":                     _prefix(text, tag),
        "parse_mode":               "HTML",
        "disable_web_page_preview": True,
    }, timeout=10)
    if resp.status_code != 200:
        print(f"텔레그램 전송 실패: {resp.text}")
    return resp.status_code == 200


def send_file(filepath, caption="", tag=""):
    """텔레그램 문서 첨부. caption에 [TAG] 접두사 부착."""
    url = f"{API_BASE}{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(filepath, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": _prefix(caption, tag)},
            files={"document": f},
            timeout=60,
        )
    if resp.status_code != 200:
        print(f"파일 전송 실패: {resp.text}")
    return resp.status_code == 200
