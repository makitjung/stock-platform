# 장중 경량 갱신: 시장 현황 + 내 종목 실시간 시세 + GitHub push만 실행 (10분 주기용)
import sys, os
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)
os.chdir(BASE_DIR)

import orchestrator

STEPS = [
    ("시장 현황",      "collector_market"),
    ("내 종목 실시간", "collector_watchlist_live"),
    ("GitHub push",    "push_data"),
]


def run():
    orchestrator._progress(f"⚡ 장중 경량 갱신 시작 ({len(STEPS)}단계)")
    ok_all = True
    for name, module in STEPS:
        ok = orchestrator.run_sequential(name, module, timeout=180)
        if not ok:
            ok_all = False
            orchestrator._progress(f"⚠️ {name} 실패 — 계속 진행")
    orchestrator._progress(f"🏁 장중 갱신 완료 — {'성공' if ok_all else '일부 실패'}")
    return ok_all


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
