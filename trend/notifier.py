# 텔레그램으로 분석 결과 요약을 전송하는 모듈

import os
import json
from datetime import datetime

from common.telegram import send_message as _send_message, send_file as _send_file

TAG = "TREND"


def load_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def send_message(text):
    return _send_message(text, tag=TAG)


def send_file(filepath, caption=""):
    return _send_file(filepath, caption=caption, tag=TAG)


def run():
    print("=== 텔레그램 알림 전송 시작 ===")

    analysis = load_json("result_analysis.json")
    today = analysis.get("date", datetime.today().strftime("%Y-%m-%d"))
    mode = analysis.get("mode", "당일")
    top50 = analysis.get("top50", [])
    total = analysis.get("total_analyzed", 0)

    google = load_json("result_google.json")
    trending_kr = [t["title"] for t in google.get("trending_kr", [])[:5]]
    trending_us = [t["title"] for t in google.get("trending_us", [])[:5]]

    strong = [x for x in top50 if x["total_score"] >= 7]
    moderate = [x for x in top50 if 4 <= x["total_score"] < 7]

    send_message(
        f"📈 <b>주식 트렌드 조기 감지 리포트</b>\n"
        f"📅 {today} | 모드: {mode}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 분석 종목: <b>{total}개</b>\n"
        f"🚨 강한 신호 (7점↑): <b>{len(strong)}개</b>\n"
        f"⚡ 관심 신호 (4~6점): <b>{len(moderate)}개</b>"
    )

    if strong:
        lines = ["🚨 <b>강한 신호 종목 (7점 이상)</b>\n━━━━━━━━━━━━━━━━━━━"]
        for i, item in enumerate(strong[:10], 1):
            kw = item["keyword"]
            score = item["total_score"]
            sig = " · ".join(item.get("signals", [])[:2])
            d3 = item.get("day3_score", 0)
            d7 = item.get("day7_score", 0)
            streak = item.get("streak_days", 1)
            trend = " 📊7일↑" if d7 > 0 else (" 📊3일↑" if d3 > 0 else "")
            streak_tag = f" 🔥{streak}일연속" if streak >= 2 else ""
            lines.append(f"{i}. <b>{kw}</b> ({score}점){streak_tag}{trend}\n   └ {sig}")
        send_message("\n".join(lines))

    if moderate:
        lines = ["⚡ <b>관심 신호 상위 종목</b>\n━━━━━━━━━━━━━━━━━━━"]
        for i, item in enumerate(moderate[:5], 1):
            kw = item["keyword"]
            score = item["total_score"]
            sig = " · ".join(item.get("signals", [])[:2])
            streak = item.get("streak_days", 1)
            streak_tag = f" 🔥{streak}일연속" if streak >= 2 else ""
            lines.append(f"{i}. <b>{kw}</b> ({score}점){streak_tag}\n   └ {sig}")
        send_message("\n".join(lines))

    trend_lines = ["🔥 <b>Google 급상승 검색어</b>\n━━━━━━━━━━━━━━━━━━━"]
    if trending_kr:
        trend_lines.append("🇰🇷 KR: " + " | ".join(trending_kr))
    if trending_us:
        trend_lines.append("🇺🇸 US: " + " | ".join(trending_us))
    send_message("\n".join(trend_lines))

    # 강신호 백테스트 요약 (7점↑ 신호 이후 수익률)
    bt = load_json("result_backtest.json")
    if bt.get("status") == "ok":
        bt_lines = []
        for hk, hv in bt.get("horizons", {}).items():
            if hv.get("sample"):
                bt_lines.append(
                    f"+{hk}거래일: 승률 <b>{hv['win_rate']}%</b> "
                    f"· 평균 {hv['avg_return']:+.2f}% (표본 {hv['sample']})"
                )
        if bt_lines:
            send_message(
                "📊 <b>강신호 적중률 (7점↑ 이후 주가)</b>\n"
                "━━━━━━━━━━━━━━━━━━━\n" + "\n".join(bt_lines)
            )

    # 증권사 리포트 요약 (워치리스트·신호 종목/섹터 매칭)
    reports = load_json("result_reports.json")
    rlist = reports.get("reports", [])
    if rlist:
        lines = [f"📑 <b>증권사 리포트</b> ({reports.get('count', len(rlist))}건 매칭)\n━━━━━━━━━━━━━━━━━━━"]
        for r in rlist[:8]:
            title = r.get("title", "")[:38]
            link = r.get("link", "")
            tag = r.get("matched", "")
            title_html = f'<a href="{link}">{title}</a>' if link else title
            lines.append(f"• [{tag}] {title_html}\n   └ {r.get('broker','')} · {r.get('date','')}")
        send_message("\n".join(lines))

    html_path = f"reports/report_{today}.html"
    if os.path.exists(html_path):
        send_file(html_path, caption=f"📄 {today} 전체 리포트 (HTML)")
        print("HTML 전송 완료.")
    else:
        print(f"리포트 파일 없음: {html_path}")

    send_message(
        f"✅ 분석 완료\n"
        f"⏰ {datetime.now().strftime('%H:%M')} | ⚠️ 투자 권유 아님, 참고용"
    )
    print("텔레그램 전송 완료.")


if __name__ == "__main__":
    run()
