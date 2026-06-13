# 텔레그램 봇으로 뉴스 메시지 전송 모듈

import sys
import json
from config import US_STOCKS
from common.telegram import send_message as _send_message

TAG         = "NEWS"
MAX_MSG_LEN = 4000  # 텔레그램 메시지 최대 4096자


def send_message(text: str, tag: str = "") -> bool:
    """단일 메시지 전송 (tag가 있으면 [TAG] 접두사 부착)"""
    return _send_message(text, tag=tag)


def send_long_message(text: str) -> None:
    """4000자 초과 시 자동 분할 전송. [NEWS] 접두사는 첫 메시지에만."""
    lines = text.split("\n")
    chunk = ""
    first = True
    for line in lines:
        if len(chunk) + len(line) + 1 > MAX_MSG_LEN:
            send_message(chunk, tag=TAG if first else "")
            first = False
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        send_message(chunk, tag=TAG if first else "")


def format_news_message(all_news: dict, date: str) -> str:
    """
    수집된 뉴스 딕셔너리를 텔레그램 HTML 메시지로 포맷
    all_news = {
      "종목명": [{"title":..., "url":..., "date":..., "source":..., "implication":...}, ...]
    }
    """
    lines = [f"<b>📰 주식 뉴스 브리핑 [{date}]</b>\n"]

    _us_names  = {s["name"] for s in US_STOCKS}
    us_stocks  = [k for k in all_news if k in _us_names]
    kr_stocks  = [k for k in all_news if k not in _us_names]

    if kr_stocks:
        lines.append("━━━━━━━━━━━━ 🇰🇷 국내 ━━━━━━━━━━━━")
        for stock in kr_stocks:
            items = all_news[stock]
            if not items:
                continue
            lines.append(f"\n<b>[{stock}]</b>")
            for item in items:
                title      = item.get("title", "")
                url        = item.get("url", "")
                source     = item.get("source", "")
                implication= item.get("implication", "")
                lines.append(f'• <a href="{url}">{title}</a> ({source})')
                if implication:
                    lines.append(f'  → {implication}')

    if us_stocks:
        lines.append("\n━━━━━━━━━━━━ 🇺🇸 미국 ━━━━━━━━━━━━")
        for stock in us_stocks:
            items = all_news[stock]
            if not items:
                continue
            lines.append(f"\n<b>[{stock}]</b>")
            for item in items:
                title      = item.get("title", "")
                url        = item.get("url", "")
                source     = item.get("source", "")
                implication= item.get("implication", "")
                lines.append(f'• <a href="{url}">{title}</a> ({source})')
                if implication:
                    lines.append(f'  → {implication}')

    return "\n".join(lines)


def send_news(all_news: dict, date: str) -> None:
    msg = format_news_message(all_news, date)
    send_long_message(msg)
    print(f"텔레그램 전송 완료 ({date})")


# CLI 실행: python3 telegram_sender.py <news_json_path> <date>
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 telegram_sender.py <news.json> <YYYY-MM-DD>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        news_data = json.load(f)

    send_news(news_data, sys.argv[2])
