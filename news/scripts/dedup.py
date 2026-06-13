# 공용 common.dedup을 news 스크립트에 재노출하는 dedup shim

import os
import sys

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
NEWS_DIR     = os.path.dirname(SCRIPT_DIR)
PLATFORM_DIR = os.path.dirname(NEWS_DIR)
if PLATFORM_DIR not in sys.path:
    sys.path.insert(0, PLATFORM_DIR)

from common.dedup import (
    normalize,
    similarity,
    deduplicate,
    deduplicate_across_stocks,
)
