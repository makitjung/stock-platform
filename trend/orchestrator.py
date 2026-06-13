# 수집기 서브에이전트를 병렬로 조율하고 파이프라인 단계를 관리하는 오케스트레이터

import subprocess
import concurrent.futures
import os
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON   = os.path.expanduser("~/.venvs/stock-platform/bin/python3")
RUNNER   = os.path.join(BASE_DIR, "agent_runner.py")

# ── 에이전트 목록 정의 ──────────────────────────────
# 전체 파이프라인 (/go)
# 각 항목: (이름, 모듈, 타임아웃(초)) — 생략 시 기본값 300 사용
AGENTS_FULL = [
    ("네이버 트렌드",  "collector_naver",    300),
    ("Google 트렌드", "collector_google",    300),
    # ("YouTube",     "collector_youtube",   300),  # 비활성: quota 부담 대비 신호 가치 낮음. 재활성 시 주석 해제.
    # ("Reddit",      "collector_reddit",    300),  # 제거됨: 핵심 키워드 대부분 0건이라 142초 비용 대비 신호 가치 낮음.
    ("DART 공시",     "collector_kind",      450),
    ("SEC EDGAR",     "collector_sec",       300),
    ("경제신문",       "collector_econ_news", 300),
    ("시장 현황",      "collector_market",   300),
]

# 빠른 파이프라인 (/go2)
AGENTS_FAST = [
    ("네이버 트렌드", "collector_naver",    300),
    ("DART 공시",     "collector_kind",     450),
    ("경제신문",      "collector_econ_news", 300),
    ("시장 현황",     "collector_market",   300),
]

# 전체 분석 체인
ANALYSIS_FULL = [
    ("신호 분석",        "analyzer"),
    ("신호 백테스트",    "backtest"),
    ("증권사 리포트",    "collector_reports"),
    ("HTML 리포트",      "report"),
    ("Excel 업데이트",   "build_excel"),
    ("AI 프롬프트",      "generate_prompt"),
    ("텔레그램 전송",    "notifier"),
    ("GitHub push",      "push_data"),
]

# 빠른 분석 체인 (리포트/Excel 생략)
ANALYSIS_FAST = [
    ("신호 분석",      "analyzer"),
    ("AI 프롬프트",    "generate_prompt"),
    ("텔레그램 전송",  "notifier"),
    ("GitHub push",    "push_data"),
]


# ── 진행 상황 출력 (PROGRESS: 접두사 → bot_server가 파싱하여 텔레그램 스트리밍) ──
def _progress(msg: str):
    print(f"PROGRESS: {msg}", flush=True)


# ── 단일 에이전트 실행 (서브프로세스) ──────────────────
def run_agent(name: str, module: str, timeout: int = 300) -> tuple:
    """
    수집기 하나를 독립 서브프로세스로 실행.
    반환: (name, ok: bool, elapsed: float)
    """
    start = time.time()
    try:
        proc = subprocess.Popen(
            [PYTHON, RUNNER, module],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout, _ = proc.communicate(timeout=timeout)
        elapsed = round(time.time() - start, 1)
        ok = proc.returncode == 0

        # 수집기 출력을 모두 기록
        for line in stdout.strip().splitlines():
            print(f"  [{name}] {line}", flush=True)

        status = "✅" if ok else "❌"
        _progress(f"{status} {name} 완료 ({elapsed}s)")
        return name, ok, elapsed

    except subprocess.TimeoutExpired:
        proc.kill()
        elapsed = round(time.time() - start, 1)
        _progress(f"⏰ {name} 타임아웃 ({timeout}s)")
        return name, False, elapsed

    except Exception as e:
        elapsed = round(time.time() - start, 1)
        _progress(f"❌ {name} 오류: {e}")
        return name, False, elapsed


# ── 병렬 실행 ────────────────────────────────────────
def run_parallel(agents: list, timeout: int = 300) -> dict:
    """
    에이전트 목록을 모두 병렬 서브프로세스로 실행.
    agents 항목은 (name, module) 또는 (name, module, timeout) 형식 모두 허용.
    반환: {name: ok}
    """
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as executor:
        futures = {}
        for agent in agents:
            name, module = agent[0], agent[1]
            t = agent[2] if len(agent) >= 3 else timeout
            futures[executor.submit(run_agent, name, module, t)] = name
        for future in concurrent.futures.as_completed(futures):
            name, ok, _ = future.result()
            results[name] = ok
    return results


# ── 순차 실행 ────────────────────────────────────────
def run_sequential(name: str, module: str, timeout: int = 120) -> bool:
    """단일 모듈을 순차 서브프로세스로 실행."""
    _progress(f"▶ {name} 실행 중...")
    _, ok, elapsed = run_agent(name, module, timeout=timeout)
    return ok


# ── 메인 파이프라인 실행 ─────────────────────────────
def run_pipeline(agents: list, analysis_steps: list, fast: bool = False) -> bool:
    """
    전체 파이프라인 실행.

    agents         : 병렬 수집기 목록 [(name, module), ...]
    analysis_steps : 순차 분석 목록  [(name, module), ...]
    fast           : True면 KRX 캐시 스킵 로직 활성화
    반환: 전체 성공 여부
    """
    import json

    start_total = time.time()
    results = {}

    # ── Phase 1: KRX 종목 수집 ──
    _progress(f"📋 [1/3] KRX 종목 수집")
    if fast:
        try:
            with open(os.path.join(BASE_DIR, "keywords_today.json"), encoding="utf-8") as f:
                data = json.load(f)
            today = datetime.today().strftime("%Y-%m-%d")
            if data.get("date") == today:
                _progress("✅ KRX 스킵 (오늘 데이터 있음)")
                results["KRX"] = True
            else:
                results["KRX"] = run_sequential("KRX 종목", "krx_symbols", timeout=120)
        except Exception:
            results["KRX"] = run_sequential("KRX 종목", "krx_symbols", timeout=120)
    else:
        results["KRX"] = run_sequential("KRX 종목", "krx_symbols", timeout=120)

    # 빠른 버전: 미수집 파일 초기화
    if fast:
        _clear_unused_results()

    # ── Phase 2: 병렬 수집 ──
    _progress(f"🔄 [2/3] 병렬 수집 시작 ({len(agents)}개 서브에이전트)")
    parallel_results = run_parallel(agents, timeout=300)
    results.update(parallel_results)
    ok_count = sum(1 for ok in parallel_results.values() if ok)
    _progress(f"✅ 병렬 수집 완료: {ok_count}/{len(agents)} 성공")

    # ── Phase 3: 분석 체인 ──
    _progress(f"📊 [3/3] 분석 체인 실행 ({len(analysis_steps)}단계)")
    for name, module in analysis_steps:
        ok = run_sequential(name, module, timeout=120)
        results[name] = ok
        if not ok:
            _progress(f"⚠️ {name} 실패 — 계속 진행")

    elapsed_total = round(time.time() - start_total)
    mins, secs = divmod(elapsed_total, 60)
    time_str = f"{mins}분 {secs}초" if mins else f"{secs}초"

    success_all = all(results.values())
    _progress(f"🏁 파이프라인 완료 ({time_str}) — {'성공' if success_all else '일부 실패'}")
    return success_all


def _clear_unused_results():
    """빠른 버전: 미수집 파일을 빈 상태로 초기화 (이전 데이터 오염 방지)"""
    import json
    today = datetime.today().strftime("%Y-%m-%d")
    empties = {
        "result_google.json":  {"date": today, "trending_kr": [], "trending_us": [], "keyword_trends": []},
        "result_youtube.json": {"date": today, "youtube": []},
        "result_reddit.json":  {"date": today, "reddit": []},
        "result_sec.json":     {"date": today, "sec": []},
    }
    for fname, empty in empties.items():
        path = os.path.join(BASE_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(empty, f, ensure_ascii=False)


# ── CLI 직접 실행 ─────────────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    if mode == "fast":
        success = run_pipeline(AGENTS_FAST, ANALYSIS_FAST, fast=True)
    else:
        success = run_pipeline(AGENTS_FULL, ANALYSIS_FULL, fast=False)
    sys.exit(0 if success else 1)
