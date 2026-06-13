# macOS 배포 교훈 — 텔레그램 봇 프로젝트에서 얻은 것들

## 1. launchd plist — 한글/유니코드 경로 사용 금지

문제: plist의 ProgramArguments, StandardOutPath, StandardErrorPath에 한글 경로를 쓰면 launchd가 파일을 열지 못한다. (exit code 78, 126)
OneDrive-개인, 주식뉴스 같은 한글 폴더명이 포함된 경로가 해당됨.

규칙:
- 실행 스크립트는 반드시 ASCII 경로에 복사: ~/bin/appname_launcher.sh
- 로그 경로는 ~/Library/Logs/appname/ 사용
- WorkingDirectory도 /tmp 또는 ~/Documents 같은 ASCII 경로 사용

## 2. 클라우드 동기화 폴더에서 chmod가 보존되지 않음

문제: OneDrive/iCloud Drive에 저장된 스크립트에 chmod +x를 해도, 동기화 과정에서 실행 권한이 사라진다.
launchd가 실행하면 exit code 126 (permission denied).

규칙:
- launchd가 실행할 스크립트는 반드시 ~/bin/ 같은 로컬 경로에 복사 후 chmod
- 원본은 클라우드에 두되, 실행 진입점(launcher)은 로컬에 위치

## 3. SCRIPT_DIR 패턴 — 복사 시 경로가 바뀜

문제: 스크립트 안에서 SCRIPT_DIR="$(dirname "${BASH_SOURCE[0]}")" 패턴을 쓰면,
스크립트를 ~/bin/으로 복사했을 때 SCRIPT_DIR이 ~/bin/으로 바뀌어 의존 파일을 못 찾는다.

규칙:
- launchd용 launcher 스크립트는 BOT_SCRIPT=절대경로 방식으로 하드코딩
- SCRIPT_DIR 상대 경로 패턴은 제자리에서만 실행되는 스크립트에만 사용

## 4. 같은 봇 토큰으로 인스턴스 2개 금지 (Telegram 409 Conflict)

문제: launchd가 봇을 이미 띄운 상태에서 수동으로 bot_server.py를 한 번 더 실행하면
Telegram API가 409 Conflict를 반환하며 두 인스턴스 모두 polling 루프가 깨진다.

규칙:
- 테스트 전 항상 pkill -9 -f bot_server.py로 기존 인스턴스 정리
- 409 발생 시 60초 대기 후 재시도하는 예외 처리를 코드에 포함
- launchctl list | grep <label>로 현재 실행 상태 먼저 확인

## 5. launchd ThrottleInterval 필수 설정

문제: KeepAlive=true인데 프로그램이 즉시 크래시 나면 launchd가 초당 수십 번 재시작을 시도한다.
CPU 낭비 + 디버깅 어려움.

규칙:
- 항상 ThrottleInterval 15 이상 설정
- 크래시 루프 확인: launchctl list | grep <label>에서 exit code가 계속 바뀌면 크래시 루프

## 6. Heredoc은 터미널 copy-paste에서 신뢰할 수 없음

문제: 멀티라인 heredoc(<< 'EOF')을 Claude가 제시하고 사용자가 복사-붙여넣기하면
따옴표 충돌, 줄바꿈 처리, 특수문자로 인해 파일이 비거나 잘리거나 SyntaxError 발생.

규칙:
- 파일 작성 시 heredoc 대신 echo 한 줄씩 >> 방식 사용
- Python -c로 파일 쓰는 경우 따옴표 중첩 주의
- 중요한 파일은 작성 후 반드시 cat으로 내용 확인

## 7. 로그가 비어 있으면 프로세스가 아예 시작 안 된 것

패턴:
- bot.log 비어 있음 + exit code 78/126 → 프로세스 시작 실패 (경로/권한 문제)
- bot.log에 launcher 출력만 있고 Python 출력 없음 → 스크립트는 실행됐지만 Python 크래시
- bot.log + bot_err.log 모두 비어 있음 → 로그 디렉토리 자체가 없음

규칙:
- 배포 전 mkdir -p ~/Library/Logs/appname/ 먼저 실행
- 진단 순서: launchctl list → 로그 확인 → 직접 bash 실행

## 8. 직접 실행으로 먼저 검증, 그 다음 launchd 등록

규칙:
- launchd 등록 전에 bash ~/bin/launcher.sh로 포그라운드 직접 실행 확인
- 직접 실행에서 정상 작동 확인 후 launchctl load
- 직접 실행 중에는 launchd 인스턴스를 언로드하고 테스트

## 9. macOS launchd exit code 해석

- exit code - (dash) → 현재 실행 중 (정상)
- exit code 0 → 정상 종료 (KeepAlive면 재시작됨)
- exit code 1 → 일반 오류 (Python 예외 등)
- exit code 2 → 스크립트 오류 (bash 명령 실패)
- exit code 78 → launchd 설정 오류 (로그 디렉토리 없음, 유니코드 경로 문제)
- exit code 126 → 실행 권한 없음 (chmod 필요)
