# OpenDART API로 국내 종목 공시 건수 급증을 감지하는 모듈 (corp_code 기준)

import json
import os
import io
import time
import zipfile
import requests
from datetime import datetime, timedelta
from lxml import etree

from common.config import DART_API_KEY

CORP_CACHE_PATH = "corp_codes.json"
CORP_CACHE_DAYS = 7  # 매핑 캐시 유효기간

# 주가에 영향이 큰 '중요 공시' 보고서명 키워드 (화이트리스트).
# 소유상황보고서·분기/반기/사업보고서·계열사거래 등 루틴 공시는 제외해 신호 질을 높인다.
MATERIAL_KEYWORDS = (
    "공급계약", "단일판매", "수주",                 # 계약·수주
    "유상증자", "무상증자", "감자",                 # 증자·감자
    "자기주식", "자사주",                           # 자기주식
    "합병", "분할", "영업양수", "영업양도", "주식교환", "양수도",  # 구조 변경
    "전환사채", "신주인수권부사채", "교환사채",       # 사채 발행
    "잠정실적", "영업(잠정)", "손익구조",            # 실적
    "최대주주변경", "경영권",                       # 지배구조
    "배당",                                         # 배당 결정
    "소송", "횡령", "배임",                         # 분쟁·사고
    "상장폐지", "관리종목", "거래정지", "불성실공시", "투자주의", # 시장 조치
    "액면분할", "주식분할",                         # 분할
    "투자판단", "타법인주식", "유형자산양수도",        # 투자 결정
    "회생절차", "부도", "영업정지",                  # 위기
)


def _count_material(disclosure_list) -> int:
    """공시 목록 중 중요 공시(MATERIAL_KEYWORDS 포함) 건수만 카운트."""
    cnt = 0
    for it in disclosure_list:
        nm = it.get("report_nm") or ""
        if any(k in nm for k in MATERIAL_KEYWORDS):
            cnt += 1
    return cnt


def _download_corp_map() -> dict:
    """OpenDART corpCode.xml(ZIP)을 받아 상장사 corp_name -> corp_code 매핑 생성."""
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    resp = requests.get(url, params={"crtfc_key": DART_API_KEY}, timeout=30)
    resp.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(resp.content))
    root = etree.fromstring(z.read(z.namelist()[0]))

    name_map = {}
    for el in root.findall("list"):
        stock = (el.findtext("stock_code") or "").strip()
        if not stock:  # 상장사(종목코드 보유)만 — 비상장·테마 매칭 방지
            continue
        name = (el.findtext("corp_name") or "").strip()
        code = (el.findtext("corp_code") or "").strip()
        if name and code:
            name_map[name] = code
    return name_map


def _load_corp_map() -> dict:
    """corp_name -> corp_code 매핑 로드. 캐시가 없거나 오래되면 재다운로드."""
    try:
        with open(CORP_CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)
        gen = datetime.strptime(cache.get("generated_at", "2000-01-01"), "%Y-%m-%d")
        if datetime.today() - gen <= timedelta(days=CORP_CACHE_DAYS) and cache.get("map"):
            return cache["map"]
    except Exception:
        pass

    try:
        name_map = _download_corp_map()
        with open(CORP_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.today().strftime("%Y-%m-%d"),
                       "map": name_map}, f, ensure_ascii=False)
        print(f"corpCode 매핑 갱신: {len(name_map)}개 상장사")
        return name_map
    except Exception as e:
        print(f"corpCode 매핑 다운로드 실패: {e}")
        # 실패 시 만료된 캐시라도 사용
        try:
            with open(CORP_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f).get("map", {})
        except Exception:
            return {}


def get_disclosures(keyword, corp_code, days=7):
    """corp_code로 특정 종목의 최근 '중요 공시' 건수 수집 (루틴 공시 제외)."""
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)

    params = {
        "crtfc_key": DART_API_KEY,
        "corp_code": corp_code,
        "bgn_de": start_date.strftime("%Y%m%d"),
        "end_de": end_date.strftime("%Y%m%d"),
        "page_count": 100,
    }
    try:
        data = requests.get("https://opendart.fss.or.kr/api/list.json",
                            params=params, timeout=10).json()
        if data.get("status") == "000":
            lst = data.get("list", [])
            material = _count_material(lst)
            return {"keyword": keyword,
                    "disclosure_count": material,            # 중요 공시 건수 (점수 산정 기준)
                    "total_count": int(data.get("total_count", 0)),  # 전체 공시 수 (참고용)
                    "source": "opendart"}
        # 013: 데이터 없음, 그 외: 0 처리
        return {"keyword": keyword, "disclosure_count": 0, "total_count": 0, "source": "opendart"}
    except Exception as e:
        print(f"DART 오류 ({keyword}): {e}")
        return {"keyword": keyword, "disclosure_count": 0, "total_count": 0, "source": "opendart"}


def run(keywords=None):
    print("=== OpenDART 공시 수집 시작 ===")

    if keywords is None:
        try:
            with open("keywords_today.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            keywords = data.get("keywords", [])
        except FileNotFoundError:
            print("keywords_today.json 없음. krx_symbols.py를 먼저 실행하세요.")
            return {}

    corp_map = _load_corp_map()

    # 한글 종목명 중 corp_code 매핑이 있는 상장사만 대상 (테마/ETF는 제외)
    korean_keywords = [kw for kw in keywords if not kw.isascii()]
    targets = [(kw, corp_map[kw]) for kw in korean_keywords if kw in corp_map]
    print(f"대상 종목 {len(targets)}개 (한글 종목명 {len(korean_keywords)}개 중 corp_code 매칭)")

    results = []
    for i, (kw, code) in enumerate(targets):
        result = get_disclosures(kw, code)
        if result["disclosure_count"] > 0:
            results.append(result)
        time.sleep(0.2)
        if (i + 1) % 50 == 0:
            print(f"진행중... {i+1}/{len(targets)}")

    results.sort(key=lambda x: x["disclosure_count"], reverse=True)

    output = {
        "date": datetime.today().strftime("%Y-%m-%d"),
        "dart": results,
    }
    with open("result_kind.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"수집 완료. 공시 있는 종목 {len(results)}개 저장 -> result_kind.json")
    return output


if __name__ == "__main__":
    run()
