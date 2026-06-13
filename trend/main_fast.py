# 빠른 파이프라인 (Naver+DART+경제신문만, 1분 이내) — orchestrator 기반
import sys, os
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)
os.chdir(BASE_DIR)

from common.crash_notify import install_excepthook
install_excepthook("trend/main_fast")

import orchestrator

def run():
    return orchestrator.run_pipeline(
        agents=orchestrator.AGENTS_FAST,
        analysis_steps=orchestrator.ANALYSIS_FAST,
        fast=True,
    )

if __name__ == "__main__":
    sys.exit(0 if run() else 1)
