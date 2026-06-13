# 전체 수집-분석-리포트-알림 파이프라인 (orchestrator 기반)
import sys, os
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)
os.chdir(BASE_DIR)

from common.crash_notify import install_excepthook
install_excepthook("trend/main")

import orchestrator

def run():
    return orchestrator.run_pipeline(
        agents=orchestrator.AGENTS_FULL,
        analysis_steps=orchestrator.ANALYSIS_FULL,
        fast=False,
    )

if __name__ == "__main__":
    sys.exit(0 if run() else 1)
