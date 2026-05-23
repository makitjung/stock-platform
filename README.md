# stock-platform

AI/stock-trend (broad scan) and AI/stock-news (watchlist briefing) merged into one repo with a shared `common/` library and a single Telegram bot. The whole platform runs autonomously on the Mac Mini via cron + launchd; no Claude Cowork dependency.

Layout:
- `common/` shared API clients (Naver, Yahoo, DART, Telegram), alarm engine, crash notifier, push utility, config loader
- `trend/` 6-source broad signal scan (네이버 트렌드 / Google / DART / SEC / 경제신문 / 시장 현황), runs daily 06:50 on Mac Mini
- `news/` 32-stock watchlist news brief — collected by `news/scripts/news_api.py` from Naver News API + Yahoo Finance RSS
- `dashboard/` Next.js dashboard deployed on Vercel, fetches data from GitHub raw
- `scripts/` cron wrappers (run_daily, run_market, run_econ_news, run_naver_datalab, watchlist_poller, rotate_logs), batch backfill, add_stock CLI
- `logs/` rotating logs (auto-compressed >1MB, pruned >30 days by `scripts/rotate_logs.py`)
- `.env` single source of API keys (chmod 600, not on git)
- `requirements.txt` unified Python deps

Venv lives at `~/.venvs/stock-platform/` (outside OneDrive to avoid binary sync corruption).

Run manually:
```
source ~/.venvs/stock-platform/bin/activate
python3 trend/main.py                  # full trend scan
python3 trend/main_fast.py             # fast trend scan
python3 news/scripts/news_api.py       # 32-stock news collection
python3 scripts/add_stock.py "엔비디아" --market us --ticker NVDA --sector "반도체/AI"
```

Schedulers on Mac Mini (crontab + launchd):
- `*/3 * * * *` watchlist_poller (GitHub watchlist.json → add_stock backfill)
- `50 6 * * *` run_daily.sh (full trend pipeline + news + GitHub push)
- `*/10 9-15 * * 1-5` run_market.sh (market snapshot + watchlist live + price/volume alarms)
- `0 7-23 * * *` run_econ_news.sh (hourly economic news + alarms)
- `30 8-22 * * *` run_naver_datalab.sh (hourly search-volume signal)
- `0 3 * * *` rotate_logs.sh (daily log rotation)
- launchd `com.stocknewsbot.plist` → `news/scripts/bot_server.py` always-on Telegram bot (/go, /go2, /news, /econ, /status, /help)

Telegram alarms (tag `ALARM` for watchlist events, `CRASH` for unhandled exceptions):
- Price ±5% spike on any watchlist stock
- Volume ≥3× previous-day volume
- News title hitting material-event keyword score ≥10 (EVENT_WEIGHTS dictionary in `common/alarm_engine.py`)

Dashboard: https://stock-platform-five.vercel.app — watchlist editor (`/api/watchlist`) + 1-year backfill panel per stock.
