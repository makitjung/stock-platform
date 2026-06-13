# 공용 common.config의 키/종목 리스트를 news 스크립트에 재노출하는 설정 shim

import os
import sys

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
NEWS_DIR     = os.path.dirname(SCRIPT_DIR)
PLATFORM_DIR = os.path.dirname(NEWS_DIR)
if PLATFORM_DIR not in sys.path:
    sys.path.insert(0, PLATFORM_DIR)

from common.config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    NAVER_CLIENT_ID, NAVER_CLIENT_SECRET,
    FMP_API_KEY,
    KR_STOCKS, US_STOCKS, ALL_STOCKS,
)

# news 스크립트의 BASE_DIR은 platform 루트가 아닌 news 폴더를 가리킴
BASE_DIR = NEWS_DIR
