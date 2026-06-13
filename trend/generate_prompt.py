# 분석 결과를 Gemini/OpenAI에 넘기기 좋은 압축 프롬프트로 변환하는 모듈

import json
import os
from datetime import datetime


def load_json(path):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def run():
    print("=== AI 프롬프트 생성 시작 ===")

    analysis = load_json("result_analysis.json")
    today = analysis.get("date", datetime.today().strftime("%Y-%m-%d"))
    mode = analysis.get("mode", "당일")
    top50 = analysis.get("top50", [])

    # 상위 15개만 압축 요약
    lines = []
    for i, item in enumerate(top50[:15], 1):
        kw = item["keyword"]
        score = item["total_score"]
        signals = item.get("signals", [])
        # 공시 노이즈 필터
        clean = []
        for s in signals:
            if "공시" in s:
                try:
                    n = int(s.replace("공시 ", "").replace("건", "").replace(",", ""))
                    if n > 500:
                        s = "공시다수"
                except Exception:
                    pass
            clean.append(s)
        sig_text = ", ".join(clean[:3])
        lines.append(f"{i}. {kw} (점수:{score}) - {sig_text}")

    # Google 급상승 검색어
    google = load_json("result_google.json")
    kr_trending = [t["title"] for t in google.get("trending_kr", [])[:5]]
    us_trending = [t["title"] for t in google.get("trending_us", [])[:5]]

    # 구글 트렌드 급증 종목
    kt = google.get("keyword_trends", [])
    kt_sorted = sorted(kt, key=lambda x: x.get("change_rate", 0), reverse=True)
    gt_lines = [f"{x['keyword']}(+{x['change_rate']}%)" for x in kt_sorted[:5] if x.get("change_rate", 0) > 50]

    prompt = f"""[주식 트렌드 분석 데이터 - {today} / 모드: {mode}]

## 검색·뉴스·공시·유튜브 통합 신호 상위 15개
{chr(10).join(lines)}

## Google 급상승 검색어
KR: {', '.join(kr_trending) if kr_trending else '없음'}
US: {', '.join(us_trending) if us_trending else '없음'}

## Google Trends 급증 종목 (7일 대비)
{', '.join(gt_lines) if gt_lines else '없음'}

---
위 데이터를 바탕으로 다음을 분석해주세요:
1. 가장 주목할 만한 종목 3개와 그 이유
2. 현재 시장에서 부각되는 섹터 테마
3. 단기 급등 가능성이 있는 종목과 주의해야 할 종목
4. 투자 시 고려할 리스크 요인
(투자 권유가 아닌 정보 분석 목적입니다)"""

    # 파일 저장
    os.makedirs("prompts", exist_ok=True)
    fname = f"prompts/prompt_{today}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"프롬프트 생성 완료 -> {fname}")
    print(f"토큰 예상: 약 {len(prompt.split())* 2}토큰 (한글 기준)")
    print("\n" + "="*50)
    print(prompt)
    print("="*50)
    return prompt


if __name__ == "__main__":
    run()
