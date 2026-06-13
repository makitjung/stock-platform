# Phase 6 — Mac Mini 스케줄러 재지정 가이드

이 작업은 반드시 Mac Mini 에서, 하나의 터미널 창에서 순서대로 진행하세요.
($PLAT 변수가 세션 내내 유지되어야 하므로 창을 닫지 마세요.)

작업 전 현재 상태를 기록해 두면 롤백이 쉽습니다:
```bash
crontab -l > ~/Desktop/cron_backup_20260521.txt 2>/dev/null
launchctl list | grep stocknews > ~/Desktop/launchd_backup_20260521.txt 2>/dev/null
echo "백업 완료"
```

---

## Step 1. 실제 경로 확인 (가장 중요)

MacBook 과 Mac Mini 의 OneDrive 폴더 이름이 다를 수 있습니다 (OneDrive-Personal vs OneDrive-개인).
아래로 실제 경로를 자동 탐지해서 $PLAT 에 저장합니다.

```bash
PLAT=$(ls -d /Users/jinhyugjung/Library/CloudStorage/OneDrive-*/AI/stock-platform 2>/dev/null | head -1)
echo "PLAT=$PLAT"
ls "$PLAT/requirements.txt" && echo "경로 확인 OK"
```

"경로 확인 OK" 가 출력되어야 다음 단계로 갑니다. 안 나오면 OneDrive 동기화가 끝났는지 확인하세요.

---

## Step 2. venv 생성 및 패키지 설치 (Mac Mini 전용)

venv 는 기기마다 따로 만들어야 합니다. OneDrive 바깥인 ~/.venvs 에 생성합니다.

```bash
mkdir -p ~/.venvs
/opt/homebrew/bin/python3 -m venv ~/.venvs/stock-platform
~/.venvs/stock-platform/bin/pip install --upgrade pip -q
~/.venvs/stock-platform/bin/pip install -r "$PLAT/requirements.txt" -q
echo "설치 완료"
~/.venvs/stock-platform/bin/python3 -c "import dotenv, telebot, pykrx, openpyxl; print('핵심 패키지 OK')"
```

"핵심 패키지 OK" 가 나와야 합니다.

---

## Step 3. 수동 테스트 (스케줄러 바꾸기 전에 먼저 확인)

빠른 trend 파이프라인을 1회 돌려봅니다 (약 1~2분, 텔레그램에 [TREND] 메시지 도착).

```bash
~/.venvs/stock-platform/bin/python3 "$PLAT/trend/main_fast.py"
```

마지막에 "파이프라인 완료" 가 나오고 텔레그램에 [TREND] 메시지가 오면 성공입니다.

---

## Step 4. cron 재지정 (trend, 매일 06:50 유지)

기존 stock-trend cron 줄을 제거하고 새 경로로 교체합니다. 스케줄(06:50)은 그대로입니다.

```bash
NEWCRON="50 6 * * * cd \"$PLAT/trend\" && \"$HOME/.venvs/stock-platform/bin/python3\" \"$PLAT/trend/main.py\" >> \"$PLAT/logs/trend/run.log\" 2>&1"
( crontab -l 2>/dev/null | grep -v "stock-trend/main.py" | grep -v "stock-platform/trend/main.py"; echo "$NEWCRON" ) | crontab -
echo "=== 현재 cron ===" && crontab -l
```

출력에 새 줄(stock-platform/trend/main.py)이 보이고, 옛 줄(stock-trend/main.py)이 사라졌는지 확인하세요.

---

## Step 5. launchd 재지정 (news 봇 상시 구동)

새 plist 를 실제 경로로 생성해서 교체합니다.

```bash
# 5-1. 기존 봇 내리기
launchctl unload ~/Library/LaunchAgents/com.stocknewsbot.plist 2>/dev/null
echo "기존 봇 중지"

# 5-2. 새 plist 생성 (bot_launcher.sh 는 venv 를 사용하도록 이미 수정됨)
mkdir -p ~/Library/Logs/stocknewsbot
cat > ~/Library/LaunchAgents/com.stocknewsbot.plist <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.stocknewsbot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$PLAT/news/scripts/bot_launcher.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>15</integer>
    <key>StandardOutPath</key>
    <string>/Users/jinhyugjung/Library/Logs/stocknewsbot/bot.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/jinhyugjung/Library/Logs/stocknewsbot/bot_err.log</string>
    <key>WorkingDirectory</key>
    <string>/tmp</string>
</dict>
</plist>
PLIST
echo "새 plist 생성 완료"

# 5-3. 새 봇 올리기
launchctl load ~/Library/LaunchAgents/com.stocknewsbot.plist
sleep 3
echo "=== 봇 상태 ===" && launchctl list | grep stocknews
echo "=== 봇 로그 ===" && tail -5 ~/Library/Logs/stocknewsbot/bot.log
```

launchctl list 에 com.stocknewsbot 이 보이고, 로그에 "[launcher] Python: ...stock-platform/bin/python3" 가 보이면 성공입니다.

---

## Step 6. 최종 확인

```bash
echo "=== cron ===" && crontab -l | grep stock-platform
echo "=== launchd ===" && launchctl list | grep stocknews
echo "=== venv ===" && ls ~/.venvs/stock-platform/bin/python3
```

세 줄 모두 정상 출력되면 Phase 6 완료입니다.
이후 7일간 매일 06:50 trend 자동 실행과 news 봇이 새 경로에서 안정적으로 도는지 확인하세요.

---

## 문제 발생 시 롤백

cron 롤백:
```bash
crontab ~/Desktop/cron_backup_20260521.txt
```

봇 롤백 (기존 외부 런처로 복귀):
```bash
launchctl unload ~/Library/LaunchAgents/com.stocknewsbot.plist
# 기존 plist 백업이 있다면 복원, 없으면 기존 ~/bin/stocknewsbot_launcher.sh 를 가리키도록 ProgramArguments 수정 후 load
```

원본 stock-trend, stock-news 폴더는 Phase 7 까지 그대로 남아 있으므로 옛 경로로도 즉시 되돌릴 수 있습니다.

---

## 참고: 키 재발급 (Phase 5 보안 마무리)

옛 stock-news/주식뉴스/scripts/config.py 와 OneDrive 버전 히스토리에 평문 키가 남아 있습니다.
아래 3개를 재발급한 뒤 $PLAT/.env 의 값만 바꾸면 전체 파이프라인이 새 키로 동작합니다.
- 네이버: developers.naver.com 앱 설정에서 Client Secret 재발급
- FMP: financialmodelingprep.com 대시보드에서 API 키 재발급
- 텔레그램: @BotFather 에서 /revoke 후 새 토큰 발급 (봇 8772029888)
