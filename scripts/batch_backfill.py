# 모든 워치리스트 종목에 대해 add_stock.py로 1년치 백필을 일괄 수행하는 1회성 스크립트

import json
import os
import sys
import time
import fcntl
import subprocess
from datetime import datetime

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)

from common.crash_notify import install_excepthook
install_excepthook("batch_backfill")

PYTHON         = os.path.expanduser("~/.venvs/stock-platform/bin/python3")
ADD_STOCK_PY   = os.path.join(BASE_DIR, "add_stock.py")
INDEX_BUILDER  = os.path.join(BASE_DIR, "build_backfill_index.py")
WATCHLIST_PATH = os.path.join(PLATFORM_DIR, "watchlist.json")
LOCK_PATH      = "/tmp/stock_platform_watchlist.lock"   # poller와 동일 락 → 동시 실행 방지


def run_one(entry: dict, market: str, idx: int, total: int) -> bool:
    name = entry["name"]
    cmd  = [PYTHON, ADD_STOCK_PY, name, "--market", market]
    if market == "us":
        cmd += ["--ticker", entry.get("ticker", "")]
    if entry.get("sector"):
        cmd += ["--sector", entry["sector"]]
    if entry.get("folder"):
        cmd += ["--folder", entry["folder"]]

    label = f"[{idx:>2d}/{total}] {market.upper()} {name}"
    start = time.time()
    print(f"=== {label} 시작 ===", flush=True)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        elapsed = round(time.time() - start, 1)
        if r.returncode == 0:
            tail = r.stdout.strip().splitlines()[-3:] if r.stdout else []
            for line in tail:
                print(f"   {line}", flush=True)
            print(f"   ✅ 완료 ({elapsed}s)", flush=True)
            return True
        else:
            print(f"   ❌ 실패 ({elapsed}s): {r.stderr.strip()[:200]}", flush=True)
            return False
    except subprocess.TimeoutExpired:
        print(f"   ⏰ 타임아웃", flush=True)
        return False


def main():
    lock_fd = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("[batch] 다른 인스턴스가 실행 중. 종료.", flush=True)
        return

    try:
        with open(WATCHLIST_PATH, encoding="utf-8") as f:
            wl = json.load(f)

        kr_list = wl.get("kr", [])
        us_list = wl.get("us", [])
        total   = len(kr_list) + len(us_list)
        print(f"--- batch backfill 시작 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 총 {total}개 ---", flush=True)

        ok_count = 0
        idx = 0
        for entry in kr_list:
            idx += 1
            if run_one(entry, "kr", idx, total):
                ok_count += 1
        for entry in us_list:
            idx += 1
            if run_one(entry, "us", idx, total):
                ok_count += 1

        print(f"\n=== 백필 완료: {ok_count}/{total} 성공 ===", flush=True)

        print("\n[batch] backfill_index.json 재생성", flush=True)
        subprocess.run([PYTHON, INDEX_BUILDER], check=False)

        print("\n[batch] GitHub push", flush=True)
        try:
            from common.push_github import push
            print(f"[batch] push 결과: {push()}", flush=True)
        except Exception as e:
            print(f"[batch] push 예외: {e}", flush=True)

        print(f"--- batch backfill 종료 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---", flush=True)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
