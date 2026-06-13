# 분석 결과를 HTML 리포트로 생성하는 모듈 (시장 현황 + 종목/섹터 분리 포함)

import json, os, time
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta
from urllib.parse import quote


def load_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def build_stock_map():
    try:
        kospi = fdr.StockListing("KOSPI")[["Code", "Name"]]
        kosdaq = fdr.StockListing("KOSDAQ")[["Code", "Name"]]
        all_stocks = pd.concat([kospi, kosdaq])
        return dict(zip(all_stocks["Name"], all_stocks["Code"]))
    except Exception:
        return {}


def get_price_change(ticker):
    try:
        today = datetime.today().strftime("%Y-%m-%d")
        week_ago = (datetime.today() - timedelta(days=10)).strftime("%Y-%m-%d")
        df = fdr.DataReader(ticker, week_ago, today)
        if df.empty or len(df) < 2:
            return None, None
        day_change = round(df["Change"].iloc[-1] * 100, 2)
        week_change = round(
            (df["Close"].iloc[-1] - df["Close"].iloc[-6 if len(df) >= 6 else 0])
            / df["Close"].iloc[-6 if len(df) >= 6 else 0] * 100, 2
        )
        return day_change, week_change
    except Exception:
        return None, None


def get_signal_badges(signals):
    colors = {
        "네이버": ("03C75A", "white"), "YouTube": ("FF0000", "white"),
        "공시":   ("1A73E8", "white"), "Google":  ("F4B400", "333"),
        "Reddit": ("FF4500", "white"), "SEC":     ("6B48FF", "white"),
        "한경":   ("1A73E8", "white"), "매경":    ("e53935", "white"),
    }
    badges = ""
    seen = set()
    for sig in signals:
        for key, (bg, fg) in colors.items():
            if key in sig and key not in seen:
                seen.add(key)
                badges += f'<span class="badge" style="background:#{bg};color:{fg};">{key}</span>'
    return badges


def format_change(val):
    if val is None:
        return '<span class="chg-none">-</span>'
    color = "#e53935" if val > 0 else ("#1e88e5" if val < 0 else "#888")
    arrow = "▲" if val > 0 else ("▼" if val < 0 else "")
    return f'<span style="color:{color};font-weight:700;">{arrow}{abs(val):.2f}%</span>'


def save_to_excel(today, top50, price_cache):
    path = "stock_trend_history.xlsx"
    rows = []
    for i, item in enumerate(top50, 1):
        kw = item["keyword"]
        d1, d7 = price_cache.get(kw, (None, None))
        signals = item.get("signals", [])
        rows.append({
            "날짜": today, "순위": i, "종목/키워드": kw,
            "총점": item["total_score"],
            "당일점수": item.get("day1_score", 0),
            "3일점수":  item.get("day3_score", 0),
            "7일점수":  item.get("day7_score", 0),
            "주가_당일(%)": d1, "주가_7일(%)": d7,
            "신호내용": " / ".join(signals[:5]),
            "소스": ", ".join(set(
                k for s in signals
                for k in ["네이버", "YouTube", "공시", "Google", "Reddit", "SEC"]
                if k in s
            ))
        })
    new_df = pd.DataFrame(rows)
    if os.path.exists(path):
        combined = pd.concat([pd.read_excel(path), new_df], ignore_index=True)
    else:
        combined = new_df
    combined.to_excel(path, index=False)
    print(f"Excel 저장 완료 -> {path} (총 {len(combined)}행)")


def market_card_html(title, emoji, items, header_bg, rate_color):
    """시장 카드 HTML (상한가/급등/급락/하한가)"""
    count = len(items)
    rows = ""
    for s in items[:20]:
        naver_url = f"https://finance.naver.com/item/main.naver?code={s['ticker']}"
        arrow = "▲" if s["change_rate"] > 0 else "▼"
        rows += f"""<tr>
            <td style="padding:6px 10px;">
                <a href="{naver_url}" target="_blank"
                   style="font-weight:600;color:#1a1f36;text-decoration:none;font-size:12px;">{s['name']}</a>
                <span style="display:block;font-size:10px;color:#9ca3af;
                             font-family:'JetBrains Mono',monospace;">{s['ticker']}</span>
            </td>
            <td style="padding:6px 10px;text-align:right;color:{rate_color};font-weight:700;
                       font-family:'JetBrains Mono',monospace;font-size:12px;">
                {arrow}{abs(s['change_rate']):.2f}%
            </td>
        </tr>"""
    if not rows:
        rows = '<tr><td colspan="2" style="padding:14px;text-align:center;color:#d1d5db;font-size:12px;">해당 없음</td></tr>'
    return f"""<div style="background:#fff;border:1px solid #e5e9f2;border-radius:12px;overflow:hidden;">
        <div style="background:{header_bg};padding:8px 12px;
                    display:flex;justify-content:space-between;align-items:center;">
            <span style="color:#fff;font-weight:700;font-size:13px;">{emoji} {title}</span>
            <span style="color:rgba(255,255,255,0.8);font-size:11px;">{count}종목</span>
        </div>
        <div style="max-height:200px;overflow-y:auto;">
            <table style="width:100%;border-collapse:collapse;"><tbody>{rows}</tbody></table>
        </div>
    </div>"""


def make_table_rows(items, price_cache, ticker_cache):
    html = ""
    for i, item in enumerate(items, 1):
        kw     = item["keyword"]
        score  = item["total_score"]
        signals = item.get("signals", [])
        d1, d3, d7 = item.get("day1_score", 0), item.get("day3_score", 0), item.get("day7_score", 0)
        badges = get_signal_badges(signals)
        signal_text = " · ".join(signals[:3])
        pd1, pd7 = price_cache.get(kw, (None, None))
        ticker   = ticker_cache.get(kw)
        naver_url = (
            f"https://finance.naver.com/item/main.naver?code={ticker}" if ticker
            else f"https://search.naver.com/search.naver?query={quote(kw)}+주가"
        )
        tier_dot   = "dot-red" if score >= 7 else ("dot-yellow" if score >= 4 else "dot-gray")
        tier_label = "강한 신호" if score >= 7 else ("관심" if score >= 4 else "감지")
        score_cls  = "sc-high" if score >= 7 else ("sc-mid" if score >= 4 else "sc-low")
        streak     = item.get("streak_days", 1)
        streak_html = (f'<span class="streak-badge">{streak}일</span>'
                       if streak >= 2 else '<span style="color:#d1d5db;">-</span>')
        html += f"""
        <tr class="data-row">
            <td class="rank-cell">{i}</td>
            <td class="keyword-cell">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span class="tier-dot {tier_dot}"></span>
                    <div>
                        <a class="keyword-name" href="{naver_url}" target="_blank">{kw}</a>
                        <span class="tier-label">{tier_label}</span>
                    </div>
                </div>
            </td>
            <td class="score-cell"><span class="score-num {score_cls}">{score}</span></td>
            <td class="num-cell">{streak_html}</td>
            <td class="num-cell">{d1 if d1 else "-"}</td>
            <td class="num-cell">{d3 if d3 else "-"}</td>
            <td class="num-cell">{d7 if d7 else "-"}</td>
            <td class="price-cell">{format_change(pd1)}</td>
            <td class="price-cell">{format_change(pd7)}</td>
            <td class="badge-cell">{badges}</td>
            <td class="signal-cell">{signal_text}</td>
        </tr>"""
    return html


def run():
    print("=== HTML 리포트 생성 시작 ===")

    analysis   = load_json("result_analysis.json")
    today      = analysis.get("date", datetime.today().strftime("%Y-%m-%d"))
    mode       = analysis.get("mode", "당일")
    top50      = analysis.get("top50", [])
    total      = analysis.get("total_analyzed", 0)

    google     = load_json("result_google.json")
    market_data = load_json("result_market.json")
    naver_data  = load_json("result_naver.json")
    econ_data   = load_json("result_econ_news.json")
    backtest    = load_json("result_backtest.json")

    strong         = len([x for x in top50 if x["total_score"] >= 7])
    trend_signals  = len([x for x in top50 if x["day3_score"] > 0 or x["day7_score"] > 0])

    print("종목 맵 구성 중...")
    stock_map = build_stock_map()

    print(f"주가 데이터 수집 중 ({len(top50)}개)...")
    price_cache  = {}
    ticker_cache = {}
    for item in top50:
        kw     = item["keyword"]
        ticker = stock_map.get(kw)
        ticker_cache[kw] = ticker
        if ticker:
            price_cache[kw] = get_price_change(ticker)
            time.sleep(0.15)
        else:
            price_cache[kw] = (None, None)

    save_to_excel(today, top50, price_cache)

    # ── 종목 / 섹터 분리 ─────────────────────────────────────────────
    stock_items  = [r for r in top50 if r.get("is_stock") is True]
    sector_items = [r for r in top50 if r.get("is_stock") is not True]

    stock_rows_html  = make_table_rows(stock_items,  price_cache, ticker_cache)
    sector_rows_html = make_table_rows(sector_items, price_cache, ticker_cache)

    def empty_row(msg):
        return f'<tr><td colspan="11" style="padding:24px;text-align:center;color:#9ca3af;">{msg}</td></tr>'

    stock_tbody  = stock_rows_html  or empty_row("개별 종목 신호 없음")
    sector_tbody = sector_rows_html or empty_row("섹터/테마 신호 없음")

    # ── 시장 현황 카드 ────────────────────────────────────────────────
    kospi  = market_data.get("kospi",  {})
    kosdaq = market_data.get("kosdaq", {})
    market_date = market_data.get("date", today)

    def mkt4(section):
        return (
            market_card_html("상한가", "🔴", section.get("상한가", []), "#ef4444", "#dc2626"),
            market_card_html("급등주", "🟠", section.get("급등",   []), "#f97316", "#ea580c"),
            market_card_html("급락주", "🔵", section.get("급락",   []), "#3b82f6", "#2563eb"),
            market_card_html("하한가", "🟣", section.get("하한가", []), "#6366f1", "#4f46e5"),
        )

    kp_u, kp_sg, kp_pl, kp_l = mkt4(kospi)
    kd_u, kd_sg, kd_pl, kd_l = mkt4(kosdaq)

    # ── 네이버 검색 추이 ──────────────────────────────────────────────
    collected_at = naver_data.get("collected_at", "")
    naver_rows = ""
    for item in naver_data.get("datalab", []):
        rate  = item.get("change_rate", 0)
        arrow = "▲" if rate > 0 else "▼" if rate < 0 else ""
        color = "#e53935" if rate > 0 else "#1e88e5" if rate < 0 else "#9ca3af"
        naver_rows += f"""<tr style="border-bottom:1px solid #f1f5f9;">
            <td style="padding:8px 14px;font-size:13px;font-weight:500;color:#374151;">{item['keyword']}</td>
            <td style="padding:8px 14px;text-align:right;font-size:12px;color:#9ca3af;
                       font-family:'JetBrains Mono',monospace;">{item.get('recent', 0):.1f}</td>
            <td style="padding:8px 14px;text-align:right;font-size:12px;font-weight:700;
                       color:{color};font-family:'JetBrains Mono',monospace;">{arrow}{abs(rate):.1f}%</td>
        </tr>"""
    if not naver_rows:
        naver_rows = '<tr><td colspan="3" style="padding:20px;text-align:center;color:#d1d5db;">데이터 없음</td></tr>'

    # ── 경제 뉴스 ─────────────────────────────────────────────────────
    econ_collected = econ_data.get("collected_at", "")
    econ_count     = f"{econ_data.get('matched_count', 0)}/{econ_data.get('total_articles', 0)}건"
    econ_rows = ""
    for article in econ_data.get("top_news", [])[:20]:
        source   = article.get("source", "")
        title    = article.get("title", "")
        link     = article.get("link", "#")
        score    = article.get("score", 0)
        kws      = article.get("matched_keywords", [])[:2]
        kw_tags  = "".join([
            f'<span style="background:#f1f5f9;color:#64748b;padding:1px 6px;'
            f'border-radius:4px;font-size:10px;margin-right:3px;">{k}</span>'
            for k in kws
        ])
        econ_rows += f"""<div style="padding:10px 14px;border-bottom:1px solid #f1f5f9;">
            <a href="{link}" target="_blank"
               style="font-size:13px;color:#374151;text-decoration:none;line-height:1.4;display:block;">{title}</a>
            <div style="margin-top:5px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                <span style="font-size:11px;color:#9ca3af;">{source}</span>
                {kw_tags}
                <span style="font-size:11px;color:#d1d5db;margin-left:auto;">점수 {score}</span>
            </div>
        </div>"""
    if not econ_rows:
        econ_rows = '<div style="padding:20px;text-align:center;color:#d1d5db;font-size:13px;">데이터 없음</div>'

    # ── 구글 트렌드 ───────────────────────────────────────────────────
    trending_kr = google.get("trending_kr", [])
    trending_us = google.get("trending_us", [])
    kr_pills = "".join([f'<span class="trend-pill">🔍 {t["title"]}</span>' for t in trending_kr]) \
               or '<span class="no-data">데이터 없음</span>'
    us_pills = "".join([f'<span class="trend-pill">🔍 {t["title"]}</span>' for t in trending_us]) \
               or '<span class="no-data">데이터 없음</span>'

    # ── 강신호 백테스트 카드 ──────────────────────────────────────────
    bt_html = ""
    if backtest.get("status") == "ok":
        bt_cards = ""
        for hk, hv in backtest.get("horizons", {}).items():
            if not hv.get("sample"):
                continue
            wr = hv["win_rate"]
            ar = hv["avg_return"]
            wcolor = "#16a34a" if wr >= 50 else "#e53935"
            acolor = "#e53935" if ar > 0 else ("#1e88e5" if ar < 0 else "#9ca3af")
            bt_cards += (
                f'<div class="bt-card"><div class="bt-h">신호 +{hk}거래일 후</div>'
                f'<div class="bt-win" style="color:{wcolor};">{wr}%</div>'
                f'<div class="bt-sub">평균 <span style="color:{acolor};font-weight:700;">{ar:+.2f}%</span> · 표본 {hv["sample"]}건</div></div>'
            )
        if bt_cards:
            bt_html = (
                '<div class="card" style="margin-bottom:16px;">'
                '<div class="card-title">🎯 강신호 적중률 '
                '<span class="card-sub">7점↑ 신호 이후 주가 · 누적 데이터 검증</span></div>'
                f'<div class="bt-grid">{bt_cards}</div></div>'
            )

    naver_at_str = f" &nbsp;·&nbsp; 네이버 기준 {collected_at}" if collected_at else ""
    econ_at_str  = f" · {econ_collected} 기준" if econ_collected else ""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>주식 트렌드 리포트 {today}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg:#f4f6fb;--surface:#fff;--surface2:#f8f9fc;--border:#e5e9f2;
    --text:#1a1f36;--text-muted:#6b7280;--accent:#2563eb;
    --red:#e53935;--yellow:#f59e0b;--green:#16a34a;--blue:#2563eb;--purple:#7c3aed;
  }}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Pretendard',-apple-system,sans-serif;background:var(--bg);color:var(--text);padding:24px 20px;}}
  .container{{max-width:1400px;margin:0 auto;}}
  .header{{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:24px 28px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;position:relative;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.05);}}
  .header::before{{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#2563eb,#7c3aed,#db2777);}}
  .header h1{{font-size:20px;font-weight:800;letter-spacing:-.5px;}}
  .header h1 span{{color:var(--accent);}}
  .header-meta{{font-size:12px;color:var(--text-muted);margin-top:4px;font-family:'JetBrains Mono',monospace;}}
  .mode-badge{{background:#eff6ff;border:1px solid #bfdbfe;color:var(--accent);padding:5px 14px;border-radius:20px;font-size:12px;font-weight:700;}}
  .stats-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;}}
  .stat-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,.04);}}
  .stat-num{{font-size:32px;font-weight:800;font-family:'JetBrains Mono',monospace;line-height:1;}}
  .stat-label{{font-size:12px;color:var(--text-muted);margin-top:5px;font-weight:500;}}
  .market-section{{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.04);}}
  .market-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}}
  .market-label{{font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;}}
  .main-grid{{display:grid;grid-template-columns:1fr 320px;gap:16px;margin-bottom:16px;}}
  .card{{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:22px 24px;box-shadow:0 1px 3px rgba(0,0,0,.04);}}
  .card-title{{font-size:14px;font-weight:700;margin-bottom:16px;padding-bottom:10px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;}}
  .card-sub{{font-size:12px;color:var(--text-muted);font-weight:400;}}
  table{{width:100%;border-collapse:collapse;font-size:13px;}}
  thead th{{background:var(--surface2);color:var(--text-muted);padding:8px 12px;text-align:left;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.5px;border-bottom:2px solid var(--border);}}
  .data-row td{{padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:middle;}}
  .data-row:last-child td{{border-bottom:none;}}
  .data-row:hover td{{background:#f8faff;}}
  .rank-cell{{color:var(--text-muted);font-family:'JetBrains Mono',monospace;font-size:12px;width:32px;text-align:center;}}
  .tier-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;}}
  .dot-red{{background:var(--red);box-shadow:0 0 0 3px rgba(229,57,53,.15);}}
  .dot-yellow{{background:var(--yellow);box-shadow:0 0 0 3px rgba(245,158,11,.15);}}
  .dot-gray{{background:#d1d5db;}}
  .keyword-name{{font-weight:700;font-size:13px;display:block;color:var(--text);text-decoration:none;}}
  .keyword-name:hover{{color:var(--accent);text-decoration:underline;}}
  .tier-label{{font-size:10px;color:var(--text-muted);margin-top:1px;display:block;}}
  .score-cell{{text-align:center;width:48px;}}
  .score-num{{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;font-weight:800;font-size:12px;font-family:'JetBrains Mono',monospace;}}
  .sc-high{{background:#fef2f2;color:var(--red);border:1.5px solid #fecaca;}}
  .sc-mid{{background:#fffbeb;color:var(--yellow);border:1.5px solid #fde68a;}}
  .sc-low{{background:#f0fdf4;color:var(--green);border:1.5px solid #bbf7d0;}}
  .num-cell{{text-align:center;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-muted);width:44px;}}
  .streak-badge{{display:inline-block;background:#fff7ed;color:#c2410c;border:1px solid #fed7aa;padding:1px 7px;border-radius:10px;font-size:11px;font-weight:700;font-family:'JetBrains Mono',monospace;}}
  .bt-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;}}
  .bt-card{{background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:14px 16px;}}
  .bt-h{{font-size:11px;color:var(--text-muted);font-weight:600;margin-bottom:6px;}}
  .bt-win{{font-size:24px;font-weight:800;font-family:'JetBrains Mono',monospace;}}
  .bt-sub{{font-size:11px;color:var(--text-muted);margin-top:3px;}}
  .price-cell{{text-align:center;width:72px;font-family:'JetBrains Mono',monospace;font-size:12px;}}
  .chg-none{{color:#d1d5db;}}
  .badge{{display:inline-block;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;margin-right:2px;margin-bottom:2px;}}
  .badge-cell{{width:140px;}}
  .signal-cell{{font-size:12px;color:var(--text-muted);line-height:1.5;}}
  .side-panel{{display:flex;flex-direction:column;gap:16px;}}
  .trend-pills{{display:flex;flex-wrap:wrap;gap:6px;}}
  .trend-pill{{background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:5px 12px;border-radius:20px;font-size:12px;font-weight:500;}}
  .no-data{{font-size:13px;color:var(--text-muted);}}
  .notice{{background:#fffbeb;border:1px solid #fde68a;color:#92400e;padding:10px 14px;border-radius:8px;font-size:12px;margin-top:14px;line-height:1.6;}}
  .divider{{height:1px;background:var(--border);margin:12px 0;}}
  .section-sep{{font-size:12px;font-weight:700;color:var(--text-muted);padding:8px 12px;background:var(--surface2);border-top:1px solid var(--border);border-bottom:1px solid var(--border);letter-spacing:.3px;}}
</style>
</head>
<body>
<div class="container">

  <!-- 헤더 -->
  <div class="header">
    <div>
      <h1>📈 주식 트렌드 <span>조기 감지</span> 리포트</h1>
      <div class="header-meta">Generated {today} {datetime.now().strftime("%H:%M")} KST &nbsp;·&nbsp; 7개 소스 통합 분석{naver_at_str}</div>
    </div>
    <div class="mode-badge">분석 모드: {mode}</div>
  </div>

  <!-- 요약 통계 -->
  <div class="stats-grid">
    <div class="stat-card"><div class="stat-num" style="color:var(--blue);">{total}</div><div class="stat-label">분석 종목 수</div></div>
    <div class="stat-card"><div class="stat-num" style="color:var(--green);">{len(top50)}</div><div class="stat-label">신호 감지 종목</div></div>
    <div class="stat-card"><div class="stat-num" style="color:var(--red);">{strong}</div><div class="stat-label">강한 신호 (7점↑)</div></div>
    <div class="stat-card"><div class="stat-num" style="color:var(--purple);">{trend_signals}</div><div class="stat-label">누적 트렌드 신호</div></div>
  </div>

  <!-- 시장 현황 -->
  <div class="market-section">
    <div style="font-size:13px;font-weight:700;color:var(--text-muted);margin-bottom:12px;">
      📊 시장 현황 <span style="font-weight:400;font-size:12px;">({market_date} 전일 기준)</span>
    </div>
    <div style="margin-bottom:14px;">
      <div class="market-label">🇰🇷 KOSPI</div>
      <div class="market-grid">{kp_u}{kp_sg}{kp_pl}{kp_l}</div>
    </div>
    <div>
      <div class="market-label">📊 KOSDAQ</div>
      <div class="market-grid">{kd_u}{kd_sg}{kd_pl}{kd_l}</div>
    </div>
  </div>

  <!-- 강신호 백테스트 -->
  {bt_html}

  <div class="main-grid">
    <div>

      <!-- 개별 종목 -->
      <div class="card" style="margin-bottom:16px;">
        <div class="card-title">
          📈 개별 종목 신호
          <span class="card-sub">{len(stock_items)}개</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>#</th><th>종목</th>
              <th style="text-align:center;">총점</th>
              <th style="text-align:center;">연속</th>
              <th style="text-align:center;">당일</th>
              <th style="text-align:center;">3일</th>
              <th style="text-align:center;">7일</th>
              <th style="text-align:center;">주가(당일)</th>
              <th style="text-align:center;">주가(7일)</th>
              <th>소스</th><th>신호 내용</th>
            </tr>
          </thead>
          <tbody>{stock_tbody}</tbody>
        </table>
        <div class="notice">※ 투자 권유가 아닌 정보 제공 목적입니다. 투자 결정은 반드시 본인 판단으로 하시기 바랍니다.</div>
      </div>

      <!-- 섹터/테마 -->
      <div class="card" style="margin-bottom:16px;">
        <div class="card-title">
          🏭 섹터/테마 신호
          <span class="card-sub">{len(sector_items)}개</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>#</th><th>키워드</th>
              <th style="text-align:center;">총점</th>
              <th style="text-align:center;">연속</th>
              <th style="text-align:center;">당일</th>
              <th style="text-align:center;">3일</th>
              <th style="text-align:center;">7일</th>
              <th style="text-align:center;">주가(당일)</th>
              <th style="text-align:center;">주가(7일)</th>
              <th>소스</th><th>신호 내용</th>
            </tr>
          </thead>
          <tbody>{sector_tbody}</tbody>
        </table>
      </div>

      <!-- 구글 트렌드 -->
      <div class="card">
        <div class="card-title">🔥 Google 급상승 검색어</div>
        <div style="margin-bottom:12px;">
          <div style="font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">🇰🇷 한국 (KR)</div>
          <div class="trend-pills">{kr_pills}</div>
        </div>
        <div class="divider"></div>
        <div>
          <div style="font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">🇺🇸 미국 (US)</div>
          <div class="trend-pills">{us_pills}</div>
        </div>
      </div>

    </div>

    <!-- 사이드 패널 -->
    <div class="side-panel">

      <!-- 네이버 검색 추이 -->
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04);">
        <div style="padding:14px 16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:14px;font-weight:700;">📈 네이버 검색 추이</span>
          {f'<span style="font-size:11px;color:var(--text-muted);">{collected_at} 기준</span>' if collected_at else ''}
        </div>
        <div style="max-height:300px;overflow-y:auto;">
          <table style="width:100%;border-collapse:collapse;"><tbody>{naver_rows}</tbody></table>
        </div>
      </div>

      <!-- 경제 뉴스 -->
      <div style="background:var(--surface);border:1px solid var(--border);border-radius:14px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04);flex:1;">
        <div style="padding:14px 16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:14px;font-weight:700;">📰 경제 뉴스</span>
          <span style="font-size:11px;color:var(--text-muted);text-align:right;">{econ_count}{econ_at_str}</span>
        </div>
        <div style="max-height:620px;overflow-y:auto;">{econ_rows}</div>
      </div>

    </div>
  </div>

</div>
</body>
</html>"""

    os.makedirs("reports", exist_ok=True)
    fname = f"reports/report_{today}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"리포트 생성 완료 -> {fname}")
    return fname


if __name__ == "__main__":
    run()
