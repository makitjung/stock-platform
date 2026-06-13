# 수집기 모듈 하나를 독립 서브프로세스로 실행하는 에이전트 래퍼

import sys
import os
import importlib
import traceback
from datetime import datetime

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PLATFORM_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PLATFORM_DIR)
os.chdir(BASE_DIR)

from common.crash_notify import install_excepthook
# 모듈명을 태그로 사용해 어느 수집기가 죽었는지 메시지로 식별
install_excepthook(f"agent_runner:{sys.argv[1] if len(sys.argv) > 1 else '?'}")


def main():
    if len(sys.argv) < 2:
        print("사용법: python agent_runner.py <module_name>", flush=True)
        sys.exit(1)

    module_name = sys.argv[1]
    start = datetime.now()

    try:
        mod = importlib.import_module(module_name)
        mod.run()
        elapsed = round((datetime.now() - start).total_seconds(), 1)
        print(f"[DONE] {module_name} ({elapsed}s)", flush=True)
        sys.exit(0)
    except Exception as e:
        elapsed = round((datetime.now() - start).total_seconds(), 1)
        print(f"[ERR] {module_name}: {e} ({elapsed}s)", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
