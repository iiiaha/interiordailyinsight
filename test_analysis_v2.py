"""새 프롬프트 기반 일일 인사이트 분석 테스트."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import anthropic
from config.settings import ANTHROPIC_API_KEY

# 1. 수집 데이터 로드
data_file = Path(__file__).resolve().parent / "data" / "crawl_20260401_215858.json"
with open(data_file, "r", encoding="utf-8") as f:
    posts = json.load(f)

print(f"총 {len(posts)}건 로드")

# 2. 게시판별 그룹화
groups: dict[str, list[str]] = {}
for p in posts:
    board = p.get("board", "기타")
    groups.setdefault(board, []).append(p["title"])

# 3. 분석용 텍스트 구성
lines = []
for board, titles in sorted(groups.items(), key=lambda x: -len(x[1])):
    lines.append(f"\n[게시판: {board}] ({len(titles)}건)")
    for t in titles:
        lines.append(f"- {t}")

aggregated = "\n".join(lines)
if len(aggregated) > 15000:
    aggregated = aggregated[:15000] + "\n\n... (이하 생략)"

print(f"분석용 텍스트: {len(aggregated)}자")

# 4. 프롬프트 설정
SYSTEM_PROMPT = """당신은 인테리어 시공업체와 인테리어 디자이너를 위한
비즈니스 인텔리전스 애널리스트입니다.

당신의 독자는 다음과 같습니다:
- 직원 1~5명 규모의 소형 인테리어 시공업체 대표
- 프리랜서 인테리어 디자이너
- 이들의 관심사: 이번 주 어디서 돈을 벌 수 있는가

당신의 역할:
- 소비자 커뮤니티 데이터를 '영업 신호'로 해석한다
- 추상적 트렌드가 아닌, 이번 주 실행 가능한 액션을 도출한다
- 모든 분석은 "그래서 업체는 어떻게 해야 하는가"로 마무리된다
- 과장하지 않는다. 데이터에 없는 것은 추측이라고 명시한다

응답 형식: 반드시 아래 JSON 구조만 반환한다.
마크다운 코드블록, 설명 텍스트 없이 순수 JSON만 출력한다."""

now = datetime.now()
generated_at = now.strftime("%Y-%m-%d %H:%M")
week_start = "2026-04-01"
week_end = "2026-04-01"

USER_PROMPT = f"""아래는 {week_start} ~ {week_end} 기간 동안
네이버 '셀프인테리어' 카페에서 수집된 게시글 {len(posts)}개입니다.

[수집 원문 데이터]
{aggregated}

---

위 데이터를 분석하여 다음 JSON 구조로 인테리어 업체 비즈니스 리포트를 작성하세요.

{{
  "meta": {{
    "period": "{week_start} ~ {week_end}",
    "total_posts_analyzed": {len(posts)},
    "report_generated_at": "{generated_at}",
    "data_quality_note": "분석 신뢰도에 영향을 주는 데이터 한계가 있다면 한 문장으로 기재, 없으면 null"
  }},

  "section1_executive_brief": {{
    "title": "오늘의 한 줄 요약",
    "one_liner": "바쁜 업체 대표가 30초 안에 오늘 시장 상황을 파악할 수 있는 핵심 문장 1개",
    "market_temperature": "뜨거움|보통|차가움",
    "market_temperature_reason": "온도 판단 근거 (게시글 수, 질문 유형, 분위기 등 데이터 기반)",
    "top3_this_week": [
      "업체가 지금 당장 알아야 할 것 1순위",
      "업체가 지금 당장 알아야 할 것 2순위",
      "업체가 지금 당장 알아야 할 것 3순위"
    ]
  }},

  "section2_demand_signals": {{
    "title": "오늘의 수요 신호 — 지금 공사 고려 중인 고객들",
    "description": "게시글 중 실제로 공사를 검토 중인 소비자 신호를 영업 관점에서 분류",
    "hot_demand": [
      {{
        "category": "수요 카테고리",
        "signal_count": "숫자",
        "urgency": "즉시|1개월 내|검토 단계",
        "urgency_basis": "urgency 판단 근거가 된 게시글 표현 예시",
        "typical_budget_mentioned": "소비자들이 언급한 예산 범위 (없으면 '언급 없음')",
        "sales_entry_point": "이 수요를 가진 고객에게 업체가 첫 연락 시 써야 할 접근법"
      }}
    ],
    "cold_demand": [
      {{
        "category": "이번 주 눈에 띄게 언급이 줄어든 수요",
        "possible_reason": "추정 이유",
        "action": "업체 조언"
      }}
    ]
  }},

  "section3_pricing_intelligence": {{
    "title": "가격 인텔리전스 — 소비자들의 돈 이야기",
    "price_resistance_points": [
      {{
        "item": "가격 저항이 감지된 공사 항목",
        "consumer_perceived_fair_price": "소비자가 적정하다고 여기는 가격대",
        "common_complaint": "가장 많이 나온 불만 표현",
        "business_implication": "업체 대응법"
      }}
    ],
    "price_acceptance_points": [
      {{
        "item": "소비자들이 수용한 공사 항목",
        "accepted_price_range": "수용된 가격대",
        "reason_for_acceptance": "수용 이유"
      }}
    ],
    "budget_signals": {{
      "low_budget_under_100": "100만원 미만 비율",
      "mid_budget_100_500": "100~500만원 비율",
      "high_budget_over_500": "500만원 이상 비율",
      "analyst_note": "특이사항"
    }},
    "quote_red_flags": ["업체가 피해야 할 견적 패턴"]
  }},

  "section4_material_trend": {{
    "title": "자재·제품 트렌드 — 지금 소비자가 원하는 것",
    "rising_materials": [
      {{
        "name": "자재 또는 제품명",
        "mention_trend": "급상승|상승|유지",
        "why_consumers_want_it": "소비자가 원하는 이유",
        "supplier_tip": "업체 활용법",
        "caution": "주의사항 (없으면 null)"
      }}
    ],
    "declining_materials": [
      {{
        "name": "하락 자재",
        "reason": "하락 이유",
        "action": "업체 대응"
      }}
    ],
    "brand_mentions": [
      {{
        "brand": "브랜드명",
        "sentiment": "긍정|중립|부정",
        "context": "언급 맥락",
        "business_note": "업체 참고사항"
      }}
    ]
  }},

  "section5_objection_map": {{
    "title": "고객 반대 논리 지도 — 영업 현장에서 바로 쓰는 대응법",
    "objections": [
      {{
        "objection": "소비자 반대 이유",
        "frequency": "높음|중간|낮음",
        "underlying_fear": "진짜 불안감",
        "counter_script": "대응 대화 예시 2~3문장",
        "proof_point": "극복 증거 유형"
      }}
    ]
  }},

  "section6_regional_signals": {{
    "title": "지역별 수요 신호",
    "active_regions": [
      {{
        "region": "지역명",
        "demand_type": "공사 유형",
        "signal_strength": "강함|보통|약함",
        "note": "특이사항"
      }}
    ],
    "analyst_note": "지역 데이터 충분성 코멘트"
  }},

  "section7_competitive_intelligence": {{
    "title": "경쟁 인텔리전스",
    "diy_vs_pro_balance": {{
      "diy_leaning_ratio": "높음|중간|낮음",
      "pro_leaning_ratio": "높음|중간|낮음",
      "swing_factors": "DIY에서 업체 고용으로 전환 계기",
      "business_action": "전환 전략 제안"
    }},
    "comparison_shopping_signals": [
      {{
        "what_consumers_compare": "비교 항목",
        "winning_factor": "이기는 요소",
        "losing_factor": "지는 요소"
      }}
    ],
    "negative_word_of_mouth": [
      {{
        "complaint_type": "부정 입소문 유형",
        "frequency": "높음|중간|낮음",
        "prevention_tip": "예방 팁"
      }}
    ]
  }},

  "section8_weekly_action": {{
    "title": "오늘 단 하나의 액션",
    "the_one_action": {{
      "action": "업체가 반드시 해야 할 단 하나의 구체적 행동",
      "why_this_week": "타이밍 근거",
      "how_to_execute": "실행 방법 3단계 이내",
      "expected_outcome": "기대 결과",
      "time_required": "소요 시간"
    }},
    "bonus_quick_wins": [
      {{
        "action": "30분 이내 실행 가능한 액션",
        "impact": "기대 효과"
      }}
    ]
  }},

  "section9_forward_look": {{
    "title": "내일 예측 & 준비",
    "next_week_demand_forecast": "수요 변화 예측",
    "seasonal_alert": "계절적 수요 변화 (해당시만)",
    "prepare_now": ["지금 준비할 것들"]
  }},

  "section10_raw_insights": {{
    "title": "오늘의 날 것의 목소리 — 소비자 직접 인용",
    "notable_quotes": [
      {{
        "quote_summary": "소비자 발언 요약",
        "why_notable": "주목 이유",
        "source_type": "질문글|후기글|불만글|추천글"
      }}
    ]
  }}
}}"""

# 5. Claude 분석
print("\nClaude 분석 요청 중... (10섹션 풀 분석, 30초~1분 소요)")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=8000,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": USER_PROMPT}],
)

raw = message.content[0].text
print(f"응답 길이: {len(raw)}자")

# JSON 파싱
try:
    if "```json" in raw:
        start = raw.index("```json") + 7
        end = raw.index("```", start)
        raw = raw[start:end]
    elif "```" in raw:
        start = raw.index("```") + 3
        end = raw.index("```", start)
        raw = raw[start:end]
    result = json.loads(raw.strip())
except json.JSONDecodeError as e:
    print(f"JSON 파싱 실패: {e}")
    # 원본 저장
    err_file = Path(__file__).resolve().parent / "data" / "analysis_v2_raw.txt"
    with open(err_file, "w", encoding="utf-8") as f:
        f.write(raw)
    print(f"원본 응답 저장: {err_file}")
    sys.exit(1)

# 결과 저장
output_file = Path(__file__).resolve().parent / "data" / "analysis_v2_20260401.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"분석 완료! 저장: {output_file}")

# 섹션 키 확인
sections = [k for k in result.keys() if k.startswith("section")]
print(f"생성된 섹션: {len(sections)}개")
for s in sections:
    title = result[s].get("title", s)
    print(f"  - {title}")
