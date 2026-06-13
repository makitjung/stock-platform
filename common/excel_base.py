# openpyxl 공용 헬퍼 (얇은 테두리, 파일 잠금 대응 저장)

import time
from openpyxl.styles import Side, Border


def thin_border(color="CCCCCC"):
    """4면 얇은 테두리 객체 반환."""
    side = Side(border_style="thin", color=color)
    return Border(left=side, right=side, top=side, bottom=side)


def save_with_retry(wb, path, attempts=3, delay=1.5):
    """엑셀 파일이 열려있을 때 발생하는 PermissionError를 재시도로 대응."""
    last_err = None
    for i in range(attempts):
        try:
            wb.save(path)
            return True
        except PermissionError as e:
            last_err = e
            if i < attempts - 1:
                print(f"[excel] 저장 재시도 {i + 1}/{attempts} — 파일 잠김 가능성")
                time.sleep(delay)
    print(f"[excel] 저장 실패: {last_err}")
    return False
