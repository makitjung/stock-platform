# GitHub push를 trend 오케스트레이터에서 실행하는 모듈

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.push_github import push


def run():
    ok = push()
    if not ok:
        raise RuntimeError("GitHub push 실패")
