# HTML 리포트를 크롬을 이용해 PDF로 변환하는 모듈

import os
import subprocess
from datetime import datetime


def run(html_path=None, pdf_path=None):
    today = datetime.today().strftime("%Y-%m-%d")

    if html_path is None:
        html_path = os.path.join("reports", f"report_{today}.html")
    if pdf_path is None:
        os.makedirs("reports", exist_ok=True)
        pdf_path = os.path.join("reports", f"report_{today}.pdf")

    if not os.path.exists(html_path):
        print(f"HTML 파일 없음: {html_path}")
        return None

    abs_html = os.path.abspath(html_path)
    abs_pdf = os.path.abspath(pdf_path)

    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]

    chrome = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome = path
            break

    if not chrome:
        print("크롬을 찾을 수 없습니다.")
        return None

    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        f"--print-to-pdf={abs_pdf}",
        "--print-to-pdf-no-header",
        "--no-pdf-header-footer",
        f"file://{abs_html}"
    ]

    print(f"PDF 변환 중: {abs_html}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if os.path.exists(abs_pdf):
        size_kb = os.path.getsize(abs_pdf) // 1024
        print(f"PDF 생성 완료 -> {abs_pdf} ({size_kb}KB)")
        return abs_pdf
    else:
        print(f"PDF 생성 실패: {result.stderr[:200]}")
        return None


if __name__ == "__main__":
    run()
