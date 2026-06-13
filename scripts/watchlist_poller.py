# GitHub의 watchlist.json 변화를 감지해 add_stock.py 백필 또는 폴더 아카이브를 수행하는 폴러

import json
import os
import shutil
import subprocess
import sys
import time
import fcntl
from datetime import datetime

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)

from common.crash_notify import install_excepthook
install_excepthook("watchlist_poller")

REPO_DIR        = os.path.expanduser("~/stock-platform-git")
WATCHLIST_LOCAL = os.path.join(PLATFORM_DIR, "watchlist.json")
WATCHLIST_REPO  = os.path.join(REPO_DIR, "watchlist.json")
LATEST_NEWS     = os.path.join(PLATFORM_DIR, "news", "latest_news.json")
ARCHIVE_BASE    = os.path.join(PLATFORM_DIR, "news", "_archive")
LOCK_PATH       = "/tmp/stock_platform_watchlist.lock"
PYTHON          = os.path.expanduser("~/.venvs/stock-platform/bin/python3")
ADD_STOCK_PY    = os.path.join(BASE_DIR, "add_stock.py")
INDEX_BUILDER   = os.path.join(BASE_DIR, "build_backfill_index.py")


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _git_pull() -> bool:
    """리포 최신 상태로 동기화. 성공 시 True."""
    try:
        r = subprocess.run(
            ["git", "-C", REPO_DIR, "pull", "--ff-only", "origin", "main"],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            print(f"[poller] git pull 실패: {r.stderr.strip()}")
            return False
        return True
    except Exception as e:
        print(f"[poller] git pull 예외: {e}")
        return False


def _names_set(watchlist: dict, key: str) -> set:
    return {s.get("name") for s in (watchlist or {}).get(key, []) if s.get("name")}


def _find_in(watchlist: dict, key: str, name: str) -> dict | None:
    for s in watchlist.get(key, []):
        if s.get("name") == name:
            return s
    return None


def _resolve_folder(entry: dict, market: str) -> str:
    if entry.get("folder"):
        return entry["folder"]
    if market == "us":
        return f"{entry.get('ticker','')}_{entry['name']}".strip("_")
    return entry["name"]


def _archive_stock_folder(market_sub: str, folder: str) -> None:
    src = os.path.join(PLATFORM_DIR, "news", market_sub, folder)
    if not os.path.isdir(src):
        print(f"[poller] 아카이브 대상 없음: {src}")
        return
    os.makedirs(ARCHIVE_BASE, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(ARCHIVE_BASE, f"{market_sub}_{folder}_{stamp}")
    shutil.move(src, dst)
    print(f"[poller] 아카이브 이동: {market_sub}/{folder} -> _archive/{os.path.basename(dst)}")


def _filter_latest_news(removed_names: set) -> None:
    """removed_names에 포함된 종목을 latest_news.json의 kr/us 배열에서 제거."""
    if not removed_names:
        return
    data = _load(LATEST_NEWS)
    if not data:
        return
    data["kr"] = [s for s in data.get("kr", []) if s.get("name") not in removed_names]
    data["us"] = [s for s in data.get("us", []) if s.get("name") not in removed_names]
    _save(LATEST_NEWS, data)
    print(f"[poller] latest_news.json에서 {len(removed_names)}개 종목 제거")


def _run_add_stock(entry: dict, market: str) -> bool:
    """add_stock.py를 서브프로세스로 실행해 1년치 백필 수행."""
    cmd = [PYTHON, ADD_STOCK_PY, entry["name"], "--market", market]
    if market == "us":
        cmd += ["--ticker", entry.get("ticker", "")]
    if entry.get("sector"):
        cmd += ["--sector", entry["sector"]]
    if entry.get("folder"):
        cmd += ["--folder", entry["folder"]]
    print(f"[poller] 백필 실행: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print(f"[poller] add_stock 실패 ({entry['name']}): {r.stderr.strip()[:300]}")
            return False
        print(r.stdout.strip()[-400:])
        return True
    except subprocess.TimeoutExpired:
        print(f"[poller] add_stock 타임아웃 ({entry['name']})")
        return False
    except Exception as e:
        print(f"[poller] add_stock 예외 ({entry['name']}): {e}")
        return False


def _run_index_builder() -> None:
    try:
        r = subprocess.run([PYTHON, INDEX_BUILDER], capture_output=True, text=True, timeout=120)
        print(r.stdout.strip() or r.stderr.strip())
    except Exception as e:
        print(f"[poller] backfill 인덱스 빌드 실패: {e}")


def _push_to_github() -> None:
    """변경된 데이터 파일을 GitHub에 푸시 (common.push_github 재사용)."""
    try:
        from common.push_github import push
        ok = push()
        print(f"[poller] push 결과: {ok}")
    except Exception as e:
        print(f"[poller] push 예외: {e}")


def run() -> None:
    if not _git_pull():
        return

    repo_wl  = _load(WATCHLIST_REPO) or {"kr": [], "us": []}
    local_wl = _load(WATCHLIST_LOCAL) or {"kr": [], "us": []}

    changed = False
    removed_names: set = set()

    for key, market, sub in (("kr", "kr", "국내"), ("us", "us", "미국")):
        repo_names  = _names_set(repo_wl, key)
        local_names = _names_set(local_wl, key)

        added   = repo_names - local_names
        removed = local_names - repo_names

        # 추가: add_stock.py로 백필
        for name in sorted(added):
            entry = _find_in(repo_wl, key, name) or {"name": name}
            ok = _run_add_stock(entry, market)
            if ok:
                changed = True

        # 제거: 폴더 아카이브
        for name in sorted(removed):
            entry = _find_in(local_wl, key, name) or {"name": name}
            folder = _resolve_folder(entry, market)
            _archive_stock_folder(sub, folder)
            removed_names.add(name)
            changed = True

    # 로컬 watchlist를 리포 상태로 정렬 (단일 출처는 GitHub)
    if repo_wl != local_wl:
        shutil.copy2(WATCHLIST_REPO, WATCHLIST_LOCAL)
        print("[poller] OneDrive watchlist.json 동기화")
        changed = True

    if removed_names:
        _filter_latest_news(removed_names)

    if changed:
        _run_index_builder()
        _push_to_github()
    else:
        print("[poller] 변경 없음")


def main():
    lock_fd = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"[poller] 다른 인스턴스가 실행 중. 종료.")
        return
    try:
        print(f"--- watchlist poller {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        run()
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
