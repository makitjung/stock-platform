# logs/ 하위 *.log 파일을 임계값 이상이면 gz 압축으로 회전하고 오래된 압축본은 삭제하는 일일 로테이터

import gzip
import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)

from common.crash_notify import install_excepthook
install_excepthook("rotate_logs")

LOGS_ROOT     = Path(PLATFORM_DIR) / "logs"
SIZE_THRESHOLD = 1 * 1024 * 1024     # 1MB 넘으면 회전
KEEP_DAYS      = 30                  # 30일 지난 .gz는 삭제


def _archive(path: Path) -> Path:
    """*.log → *.log.YYYYMMDDHHMMSS.gz로 압축 이동, 원본은 빈 파일로 남김."""
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    target = path.with_suffix(path.suffix + f".{stamp}.gz")
    with open(path, "rb") as src, gzip.open(target, "wb") as dst:
        shutil.copyfileobj(src, dst)
    # 원본을 비워서 진행 중인 append 핸들이 끊기지 않도록 truncate (rm+touch 대신)
    with open(path, "w"):
        pass
    return target


def _prune_old(directory: Path) -> int:
    """KEEP_DAYS 지난 *.gz 삭제. 삭제 개수 반환."""
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    removed = 0
    for gz in directory.rglob("*.gz"):
        try:
            mtime = datetime.fromtimestamp(gz.stat().st_mtime)
            if mtime < cutoff:
                gz.unlink()
                removed += 1
        except Exception as e:
            print(f"  [prune] {gz} 실패: {e}")
    return removed


def main():
    print(f"--- rotate_logs {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    if not LOGS_ROOT.exists():
        print("logs/ 디렉토리 없음. 종료.")
        return

    rotated = 0
    for log in LOGS_ROOT.rglob("*.log"):
        try:
            size = log.stat().st_size
        except FileNotFoundError:
            continue
        if size < SIZE_THRESHOLD:
            continue
        target = _archive(log)
        print(f"  rotate: {log.relative_to(LOGS_ROOT)} ({size:,}B) -> {target.name}")
        rotated += 1

    removed = _prune_old(LOGS_ROOT)
    print(f"회전 {rotated}건, {KEEP_DAYS}일 초과 압축본 삭제 {removed}건")


if __name__ == "__main__":
    main()
