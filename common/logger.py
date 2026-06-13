# 파이프라인별 회전 로그 파일 핸들러를 생성하는 모듈

import logging
import os
from logging.handlers import RotatingFileHandler

from common.config import LOGS_DIR


def get_logger(tag, level=logging.INFO):
    """tag별 logs/{tag}/run.log 회전 로거 반환. 동일 tag 재호출 시 같은 인스턴스."""
    name = f"stock-platform.{tag}"
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_dir = os.path.join(LOGS_DIR, tag)
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, "run.log")

    handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(fmt)

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)

    logger.addHandler(handler)
    logger.addHandler(stream)
    logger.setLevel(level)
    return logger
