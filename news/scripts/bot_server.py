# 텔레그램 양방향 봇 서버 — /news 명령으로 주식 뉴스 수집 트리거

import os
import sys
import json
import time
import datetime
import threading
import traceback
import subprocess

import telebot
from telebot.types import Message

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from news_api import collect_all_news, format_telegram_message, save_news_to_json, run_news_alerts
from stock_excel import save_stock_news_excel

# common은 stock-platform 루트 기준
_PLAT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PLAT_DIR not in sys.path:
    sys.path.insert(0, _PLAT_DIR)
from common.push_github import push as _push_github
from common.crash_notify import install_excepthook
install_excepthook("bot_server")

# ─── 봇 초기화 ────────────────────────────────────────────────
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ─── 경로 ─────────────────────────────────────────────────────
TREND_DIR  = os.path.join(_PLAT_DIR, "trend")
TREND_PY   = os.path.expanduser("~/.venvs/stock-platform/bin/python3")
ECON_PATH  = os.path.join(TREND_DIR, "result_econ_news.json")

# ─── 상태 관리 ────────────────────────────────────────────────
_state = {
    "last_run":    None,   # 마지막 뉴스 수집 시각 (datetime)
    "is_running":  False,  # 현재 뉴스 수집 중 여부
    "last_count":  0,      # 마지막 수집 건수
    "run_count":   0,      # 총 실행 횟수
}

# 트렌드 파이프라인(/go, /go2) 동시 실행 방지
_trend_lock    = threading.Lock()
_trend_running = False
_trend_cmd     = ""


# ─── 권한 확인 ────────────────────────────────────────────────
def _is_authorized(message: Message) -> bool:
    """등록된 chat_id에서 온 메시지만 허용."""
    return str(message.chat.id) == str(TELEGRAM_CHAT_ID)


def _check_auth(message: Message) -> bool:
    if not _is_authorized(message):
        bot.reply_to(message, "⛔ 권한이 없습니다.")
        return False
    return True


# ─── 뉴스 수집 실행 (별도 스레드) ────────────────────────────
def _run_collection(chat_id: int) -> None:
    """뉴스 수집 전체 파이프라인 실행."""
    if _state["is_running"]:
        bot.send_message(chat_id, "⚠️ 이미 수집 중입니다. 잠시 후 다시 시도하세요.")
        return

    _state["is_running"] = True
    today = datetime.date.today().isoformat()

    try:
        bot.send_message(chat_id, f"⏳ <b>뉴스 수집 시작</b> — {today}\n32개 종목 수집 중...")

        start = time.time()
        all_news = collect_all_news(today)
        elapsed = time.time() - start

        # JSON 저장 (대시보드용)
        save_news_to_json(all_news, today)

        # 종목별 Excel 저장
        save_stock_news_excel(all_news, today)

        # 핵심 키워드 뉴스 알람 (점수 임계값 이상이면 별도 텔레그램 발송)
        try:
            fired = run_news_alerts(all_news)
            if fired:
                print(f"[뉴스 알람] {fired}건 발송")
        except Exception as e:
            print(f"[뉴스 알람] 실패: {e}")

        # 통계
        total = sum(len(v) for v in all_news.values())
        _state["last_run"]   = datetime.datetime.now()
        _state["last_count"] = total
        _state["run_count"] += 1

        # 요약 먼저 전송
        summary = (
            f"✅ <b>수집 완료</b> ({elapsed:.0f}초)\n"
            f"총 <b>{total}건</b> 수집 | 종목 <b>{len(all_news)}개</b>\n"
        )
        bot.send_message(chat_id, summary)

        # 본문 메시지 (길면 분할)
        msg = format_telegram_message(all_news, today)
        _send_long(chat_id, msg)

        # Excel 업데이트 시도 (실패해도 계속)
        _try_excel_update(all_news, today)

        # GitHub push (실패해도 계속)
        try:
            _push_github()
        except Exception as pe:
            print(f"[GitHub push 실패]: {pe}")

    except Exception as e:
        err = traceback.format_exc()
        print(f"[수집 오류]\n{err}")
        bot.send_message(chat_id, f"❌ 수집 중 오류 발생:\n<code>{str(e)[:200]}</code>")
    finally:
        _state["is_running"] = False


def _try_excel_update(all_news: dict, today: str) -> None:
    """Excel 업데이트 — 직접 import 방식으로 subprocess 의존성 제거."""
    try:
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from excel_writer import bulk_update

        # excel_writer가 기대하는 스키마로 implication 키 부여
        normalized = {}
        for stock_name, items in all_news.items():
            normalized[stock_name] = [
                {
                    "title":       it.get("title", ""),
                    "url":         it.get("url", ""),
                    "date":        it.get("date", ""),
                    "source":      it.get("source", ""),
                    "implication": "",
                }
                for it in items
            ]

        bulk_update(normalized, today)
        print("[Excel 업데이트 완료]")
    except Exception as e:
        import traceback
        print(f"[Excel 업데이트 실패]: {e}")
        print(traceback.format_exc())


def _send_long(chat_id: int, text: str, chunk: int = 3800) -> None:
    """4000자 초과 메시지를 줄 단위로 분할 전송 (HTML 태그 중간 절단 방지)."""
    if len(text) <= chunk:
        bot.send_message(chat_id, text)
        return

    lines = text.split("\n")
    current_lines: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > chunk and current_lines:
            bot.send_message(chat_id, "\n".join(current_lines))
            time.sleep(0.4)
            current_lines = [line]
            current_len = line_len
        else:
            current_lines.append(line)
            current_len += line_len

    if current_lines:
        bot.send_message(chat_id, "\n".join(current_lines))


# ─── 명령 핸들러 ──────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(message: Message) -> None:
    if not _check_auth(message):
        return
    text = (
        "👋 <b>주식 플랫폼 봇 가동 중</b>\n\n"
        "사용 가능한 명령:\n"
        "/news — 32종목 워치리스트 뉴스 수집\n"
        "/go   — 트렌드 전체 파이프라인 (5~10분)\n"
        "/go2  — 트렌드 빠른 파이프라인 (1분 이내)\n"
        "/econ — 경제 주요 기사 10건\n"
        "/status — 실행 상태 확인\n"
        "/help — 도움말\n"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["help"])
def cmd_help(message: Message) -> None:
    if not _check_auth(message):
        return
    text = (
        "<b>📖 도움말</b>\n\n"
        "<b>/news</b>\n"
        "  국내 16 + 미국 16개 종목의 최신 뉴스를 수집합니다.\n"
        "  Naver News API + Yahoo Finance RSS를 사용합니다.\n"
        "  수집에 약 30~60초 소요됩니다.\n\n"
        "<b>/go</b> / <b>/go2</b>\n"
        "  /go  — 7개 소스 전체 트렌드 분석 (Google Trends 포함, 5~10분)\n"
        "  /go2 — 빠른 트렌드 분석 (Naver + DART + 경제뉴스 + 시장, 1분 내외)\n\n"
        "<b>/econ</b>\n"
        "  중요도 기준 경제 주요 기사 10건을 한경/매경/RSS 등에서 추려 전송합니다.\n\n"
        "<b>/status</b>\n"
        "  마지막 수집/실행 상태를 표시합니다.\n\n"
        "<b>자동 실행</b>\n"
        "  cron 06:50 — trend/main.py 일일 파이프라인 (Mac Mini)\n"
        "  launchd — bot_server.py 항시 가동 (수동 명령 수신)\n"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["status"])
def cmd_status(message: Message) -> None:
    if not _check_auth(message):
        return
    lr = _state["last_run"]
    trend_line = (
        f"트렌드: 🔄 실행 중 ({_trend_cmd})" if _trend_running else "트렌드: 💤 대기"
    )
    if lr:
        last = lr.strftime("%Y-%m-%d %H:%M:%S")
        news_line = (
            f"마지막 수집: {last}\n"
            f"수집 건수: {_state['last_count']}건\n"
            f"총 실행 횟수: {_state['run_count']}회\n"
            f"뉴스: {'⏳ 수집 중' if _state['is_running'] else '✅ 대기'}"
        )
    else:
        news_line = "뉴스: 아직 수집 기록 없음. /news 로 시작하세요."
    bot.send_message(message.chat.id, f"<b>📊 봇 상태</b>\n\n{news_line}\n{trend_line}")


@bot.message_handler(commands=["news"])
def cmd_news(message: Message) -> None:
    if not _check_auth(message):
        return
    # 별도 스레드에서 실행 (봇 blocking 방지)
    t = threading.Thread(
        target=_run_collection,
        args=(message.chat.id,),
        daemon=True
    )
    t.start()


# ─── 트렌드 파이프라인 실행 (/go, /go2) ───────────────────────
def _run_trend_pipeline(chat_id: int, script_name: str, label: str) -> None:
    """trend/main.py 또는 main_fast.py를 서브프로세스로 실행하고
    stdout의 PROGRESS: 라인을 텔레그램으로 스트리밍."""
    global _trend_running, _trend_cmd

    bot.send_message(chat_id, f"⏳ <b>{label} 시작</b>")
    start = time.time()
    log_dir  = os.path.join(TREND_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "run.log")

    try:
        proc = subprocess.Popen(
            [TREND_PY, os.path.join(TREND_DIR, script_name)],
            cwd=TREND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        pending: list[str] = []
        last_send = time.time()

        with open(log_path, "a", encoding="utf-8") as log_f:
            log_f.write(f"\n[{datetime.datetime.now()}] {label} 시작\n")
            for line in proc.stdout:
                line = line.rstrip()
                log_f.write(line + "\n")
                log_f.flush()
                if line.startswith("PROGRESS:"):
                    pending.append(line[len("PROGRESS:"):].strip())
                    now = time.time()
                    if pending[-1].startswith("🏁") or now - last_send >= 3:
                        bot.send_message(chat_id, "\n".join(pending))
                        pending = []
                        last_send = now
            if pending:
                bot.send_message(chat_id, "\n".join(pending))

        proc.wait()
        elapsed = int(time.time() - start)
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins}분 {secs}초" if mins else f"{secs}초"
        if proc.returncode != 0:
            bot.send_message(chat_id, f"⚠️ 일부 단계 실패 | ⏱ {time_str}\n📋 trend/logs/run.log 확인")
    except Exception as e:
        bot.send_message(chat_id, f"❌ <b>실행 오류</b>: {e}")
    finally:
        with _trend_lock:
            _trend_running = False
            _trend_cmd     = ""


# ─── 경제 뉴스 주요 기사 전송 (/econ) ─────────────────────────
def _send_econ_news(chat_id: int) -> None:
    """trend/result_econ_news.json의 중요도 상위 10건을 전송. 오늘 데이터 없으면 즉석 수집."""
    today = datetime.date.today().isoformat()

    fresh = False
    try:
        with open(ECON_PATH, encoding="utf-8") as f:
            cached = json.load(f)
        fresh = cached.get("date") == today
    except Exception:
        pass

    if not fresh:
        bot.send_message(chat_id, "⏳ 경제 뉴스 수집 중 (RSS + Naver)...")
        try:
            subprocess.run(
                [TREND_PY, os.path.join(TREND_DIR, "agent_runner.py"), "collector_econ_news"],
                cwd=TREND_DIR,
                check=True,
                timeout=300,
            )
        except Exception as e:
            bot.send_message(chat_id, f"❌ 뉴스 수집 실패: {e}")
            return

    try:
        with open(ECON_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        bot.send_message(chat_id, f"❌ 뉴스 파일 로드 실패: {e}")
        return

    top_news = data.get("top_news") or data.get("top20", [])
    if not top_news:
        bot.send_message(chat_id, "📰 오늘 수집된 주요 기사가 없습니다.")
        return

    total = data.get("total_articles", 0)
    bot.send_message(
        chat_id,
        f"📰 <b>경제 주요 뉴스 브리핑</b>\n"
        f"📅 {data.get('date', today)} | 전체 {total}건 수집\n"
        f"━━━━━━━━━━━━━━━━━━━",
    )

    articles = top_news[:10]
    for batch_start in range(0, len(articles), 5):
        batch = articles[batch_start:batch_start + 5]
        lines = []
        for i, art in enumerate(batch, batch_start + 1):
            source  = art.get("source", "")
            title   = art.get("title", "")
            desc    = art.get("desc", "")
            link    = art.get("link", "")  # econ 데이터는 link 키 사용 (별도 계약)
            imp     = art.get("importance", art.get("score", 0))
            via     = "🔵" if art.get("via") == "naver_api" else "📰"
            link_tag = f'<a href="{link}">기사 보기</a>'
            desc_short = desc[:80] + "..." if len(desc) > 80 else desc
            lines.append(
                f"{i}. {via} <b>[{source}]</b> {title}\n"
                f"   └ {desc_short}\n"
                f"   🔥 중요도 {imp}점 | 🔗 {link_tag}"
            )
        bot.send_message(chat_id, "\n\n".join(lines))


# ─── 트렌드/경제 명령 핸들러 ─────────────────────────────────
@bot.message_handler(commands=["go", "go2"])
def cmd_go(message: Message) -> None:
    global _trend_running, _trend_cmd
    if not _check_auth(message):
        return
    cmd = message.text.strip().split()[0]
    if cmd == "/go":
        script, label = "main.py", "전체 파이프라인 (/go)"
    else:
        script, label = "main_fast.py", "빠른 파이프라인 (/go2)"

    with _trend_lock:
        if _trend_running:
            bot.send_message(
                message.chat.id,
                f"⚠️ <b>{_trend_cmd}</b> 실행 중입니다. 완료 후 다시 시도하세요.",
            )
            return
        _trend_running = True
        _trend_cmd     = cmd

    t = threading.Thread(
        target=_run_trend_pipeline,
        args=(message.chat.id, script, label),
        daemon=True,
    )
    t.start()


@bot.message_handler(commands=["econ"])
def cmd_econ(message: Message) -> None:
    if not _check_auth(message):
        return
    bot.send_message(message.chat.id, "🔍 경제 주요 기사 조회 중...")
    t = threading.Thread(target=_send_econ_news, args=(message.chat.id,), daemon=True)
    t.start()


# ─── 알 수 없는 명령 처리 ─────────────────────────────────────
@bot.message_handler(func=lambda m: True)
def echo_unknown(message: Message) -> None:
    if not _is_authorized(message):
        return
    bot.reply_to(message, "❓ 알 수 없는 명령입니다. /help 를 입력하세요.")


# ─── 메인 루프 ────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[봇 시작] {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"토큰: ...{TELEGRAM_BOT_TOKEN[-10:]}")
    print(f"허용 chat_id: {TELEGRAM_CHAT_ID}")
    print("Ctrl+C 로 종료")

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=20)
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 409:
                print(f"[409 충돌] 다른 인스턴스 감지. 즉시 종료 (launchd가 재시작 관리).")
                sys.exit(0)
            else:
                print(f"[Telegram API 오류, 10초 후 재시작]: {e}")
                time.sleep(10)
        except Exception as e:
            print(f"[polling 오류, 10초 후 재시작]: {e}")
            time.sleep(10)
