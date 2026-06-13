# GitHub stock-platform 저장소에 데이터 파일을 push하는 공용 유틸리티

import os
import glob
import shutil
import subprocess
import fcntl
from datetime import datetime

LOCK_PATH = "/tmp/stock_platform_push.lock"

REPO_DIR = os.path.expanduser("~/stock-platform-git")

_FILES = [
    ("trend/result_analysis.json",       "trend/result_analysis.json"),
    ("trend/result_econ_news.json",      "trend/result_econ_news.json"),
    ("trend/result_naver.json",          "trend/result_naver.json"),
    ("trend/result_market.json",         "trend/result_market.json"),
    ("trend/result_dates.json",          "trend/result_dates.json"),
    ("trend/result_google.json",         "trend/result_google.json"),
    ("trend/result_backtest.json",       "trend/result_backtest.json"),
    ("trend/result_watchlist_live.json", "trend/result_watchlist_live.json"),
    ("trend/result_reports.json",        "trend/result_reports.json"),
    ("news/latest_news.json",            "news/latest_news.json"),
    ("news/backfill_index.json",         "news/backfill_index.json"),
    ("watchlist.json",                   "watchlist.json"),
]


def _find_platform() -> str:
    matches = glob.glob(os.path.expanduser("~/Library/CloudStorage/OneDrive-*/AI/stock-platform"))
    if matches:
        return matches[0]
    # fallback: 이 파일 기준 한 단계 위 (common/ → stock-platform/)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def push(files: list[tuple] | None = None) -> bool:
    """
    데이터 파일을 ~/stock-platform-git 으로 복사 후 GitHub push.
    files: (플랫폼 상대경로, 저장소 상대경로) 튜플 목록. None 이면 _FILES 기본 목록.
    반환값: 성공 여부.
    """
    if not os.path.isdir(os.path.join(REPO_DIR, ".git")):
        print(f"[push_github] {REPO_DIR} 가 git 저장소가 아닙니다.")
        print(f"[push_github] 먼저 'git clone https://github.com/makitjung/stock-platform ~/stock-platform-git' 을 실행하세요.")
        return False

    plat = _find_platform()
    targets = files or _FILES

    for rel_src, rel_dst in targets:
        src = os.path.join(plat, rel_src)
        dst = os.path.join(REPO_DIR, rel_dst)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  [push] 복사: {rel_src}")
        else:
            print(f"  [push] 없음 (스킵): {rel_src}")

    # 날짜별 스냅샷 파일 복사 (history/YYYY-MM-DD/)
    _HISTORY_FILES = ["result_analysis.json", "result_naver.json", "result_market.json"]
    history_src_base = os.path.join(plat, "trend", "history")
    if os.path.isdir(history_src_base):
        for date_dir in sorted(os.listdir(history_src_base)):
            for hfile in _HISTORY_FILES:
                src = os.path.join(history_src_base, date_dir, hfile)
                if os.path.exists(src):
                    rel_dst = f"trend/history/{date_dir}/{hfile}"
                    dst = os.path.join(REPO_DIR, rel_dst)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    print(f"  [push] 복사: {rel_dst}")

    def _git(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(["git"] + args, cwd=REPO_DIR, capture_output=True, text=True)

    lock_fd = open(LOCK_PATH, "w")
    fcntl.flock(lock_fd, fcntl.LOCK_EX)
    try:
        _git(["add", "trend/", "news/", "trend/history/", "watchlist.json"])
        if _git(["diff", "--cached", "--quiet"]).returncode == 0:
            print("[push_github] 변경 없음, push 스킵")
            return True

        commit_msg = f"data: {datetime.today().strftime('%Y-%m-%d %H:%M')}"
        _git(["commit", "-m", commit_msg])
        result = _git(["push", "origin", "main"])
        if result.returncode == 0:
            print(f"[push_github] push 완료: {commit_msg}")
            return True

        # non-fast-forward 등 충돌 시 rebase 후 재시도
        print(f"[push_github] push 실패, rebase 후 재시도: {result.stderr.strip()}")
        pull = _git(["pull", "--rebase", "origin", "main"])
        if pull.returncode != 0:
            print(f"[push_github] rebase 실패: {pull.stderr.strip()}")
            return False
        result = _git(["push", "origin", "main"])
        if result.returncode == 0:
            print(f"[push_github] push 완료 (재시도): {commit_msg}")
            return True
        else:
            print(f"[push_github] push 최종 실패: {result.stderr.strip()}")
            return False
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
