"""v6: 고인게이지먼트 기반 시그널 분석."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import anthropic
from config.settings import ANTHROPIC_API_KEY
from processor.signal_extractor import filter_high_engagement, build_analysis_text

# 1. 데이터 로드
data_file = Path(__file__).resolve().parent / "data" / "crawl_full_20260401.json"
with open(data_file, "r", encoding="utf-8") as f:
    posts = json.load(f)

print(f"total: {len(posts)}")

# 2. 고인게이지먼트 필터
high = filter_high_engagement(posts, min_comments=15)
print(f"high engagement: {len(high)}")

# 3. 분석용 텍스트
aggregated = build_analysis_text(posts, high)
print(f"analysis text: {len(aggregated):,} chars")

# 4. 프롬프트
SYSTEM_PROMPT = """당신은 연간 수천만 원의 컨설팅 피를 받는 인테리어 업계 비즈니스 인텔리전스 애널리스트입니다.

독자: 소형 인테리어 시공업체 대표, 프리랜서 인테리어 디자이너.

분석 원칙:
- 댓글이 많은 게시글이 시장의 진짜 시그널입니다. 댓글 수에 비례하여 중요도를 판단하십시오.
- "필름시공", "턴키", "도배" 같은 범용 키워드가 아니라, "영림 PS170", "디아망 회크화", "에디톤 솔티크림" 같은 구체적 제품명/모델명을 추출하십시오.
- 소비자가 실제로 비교하는 제품 조합 (A vs B)을 찾아내십시오.
- 견적/가격이 언급된 경우 평형별로 정리하십시오.
- 업체명이 추천되거나 불만 대상이 된 경우 반드시 포함하십시오.
- 공급망 이슈, 자재 수급 위기 등 시장 레벨 시그널을 놓치지 마십시오.

톤앤매너:
- 전문 컨설턴트가 고액 고객에게 보고하는 격식 있는 존댓말.
- "~하십시오", "~하시기 바랍니다", "~을 권장합니다".
- 소비자 발언을 인용할 때는 반드시 재구성하여 "~라는 의견이 다수 확인되었습니다" 식으로 작성.

응답: 순수 JSON만. 코드블록 없이."""

USER_PROMPT = f"""아래는 2026-04-01 하루 동안 네이버 '셀프인테리어' 카페에서 수집된 {len(posts)}개의 게시글입니다.
댓글 15개 이상의 고인게이지먼트 게시글 {len(high)}건은 본문+댓글 전체를 포함했고,
나머지는 제목만 포함했습니다.

{aggregated}

---

위 데이터를 분석하여 다음 JSON을 작성하십시오.

중요 규칙:
- section1(제품 시그널)과 section6(오늘의 액션)은 필수입니다.
- section2~5는 해당 데이터가 확인된 경우에만 작성하십시오.
- 데이터에 비교글이 없으면 section2의 battles를 빈 배열로 반환하십시오.
- 가격 데이터가 없으면 section3의 price_data를 빈 배열로 반환하십시오.
- 불만/분쟁 글이 없으면 section4의 pains를 빈 배열로 반환하십시오.
- 시장 레벨 시그널이 없으면 section5의 signals를 빈 배열로 반환하십시오.
- 억지로 만들지 마십시오. 없으면 없는 것입니다.

{{
  "meta": {{
    "date": "2026-04-01",
    "total_posts": {len(posts)},
    "high_engagement_posts": {len(high)},
    "generated_at": "{datetime.now().strftime('%Y-%m-%d %H:%M')}"
  }},

  "section1_hot_products": {{
    "title": "오늘의 제품/자재 시그널 TOP 10",
    "products": [
      {{
        "rank": 1,
        "product": "자연스러운 제품명 (예: '디아망 회크화', '영림 PS170', '에디톤 솔티크림', '올바른도배 일산점'). 브랜드+제품을 자연스럽게 붙여 쓰기.",
        "category": "벽지|마루|필름|조명|수전|중문|실링팬|업체|기타",
        "signal_tag": "강추|비교중|불만|수급이슈|신제품",
        "one_line": "핵심 시그널 한 줄 (15자 이내, 명사형 종결. 예: '프리미엄 도배 1순위 자리 굳힘')",
        "action": "업체 대응 인사이트 2~3문장. 구체적이고 실무적으로 작성. 왜 이 시그널이 중요한지, 어떻게 대응해야 하는지, 기대 효과는 무엇인지를 포함. 존댓말."
      }}
    ]
  }},

  "section2_product_battles": {{
    "title": "소비자가 지금 비교하고 있는 것",
    "battles": [
      {{
        "product_a": "제품A",
        "product_b": "제품B",
        "category": "카테고리",
        "context": "왜 이 두 제품이 비교되고 있는지 배경 1줄",
        "action": "업체 대응 인사이트 2~3문장. 이 비교 상황에서 업체가 어떻게 포지셔닝해야 하는지 구체적으로. 존댓말."
      }}
    ]
  }},

  "section3_price_intel": {{
    "title": "오늘의 가격 인텔리전스",
    "price_data": [
      {{
        "scope": "공사 범위 (예: 21평 턴키)",
        "price": "구체적 금액 (예: 3,700만원)",
        "includes": "포함 항목 (짧게)",
        "action": "업체 대응 인사이트 2~3문장. 이 가격 데이터를 업체가 어떻게 활용해야 하는지. 존댓말."
      }}
    ]
  }},

  "section4_consumer_pain": {{
    "title": "오늘의 소비자 불만 시그널",
    "pains": [
      {{
        "headline": "문제 핵심 한 줄 (15자 이내, 명사형. 예: '입주청소 불량 서비스')",
        "severity": "심각|주의|참고",
        "detail": "상황 설명 1~2문장 (재구성)",
        "action": "업체 예방/대응 인사이트 2~3문장. 구체적 대응법과 기대효과. 존댓말."
      }}
    ]
  }},

  "section5_market_signal": {{
    "title": "시장 레벨 시그널",
    "signals": [
      {{
        "headline": "시그널 핵심 한 줄 (15자 이내, 명사형. 예: '중동 전쟁發 자재 수급 위기')",
        "detail": "상황 설명 1~2문장 (재구성)",
        "impact": "업체 영향 한 줄",
        "action": "대응 방안 한 줄 (~하십시오)"
      }}
    ]
  }},

  "section6_one_action": {{
    "title": "오늘의 액션",
    "action": "오늘 업체가 실행할 구체적 행동 1줄 (~하십시오)",
    "why": "근거 1줄",
    "how": "실행법 3단계 (각 1줄)"
  }}
}}"""

# 5. Claude 분석
print("\nClaude analysis...")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=8000,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": USER_PROMPT}],
)

raw = message.content[0].text
print(f"response: {len(raw):,} chars")

text = raw.strip()
if "```json" in text:
    text = text[text.index("```json")+7:text.index("```", text.index("```json")+7)]
elif "```" in text:
    text = text[text.index("```")+3:text.index("```", text.index("```")+3)]

try:
    result = json.loads(text.strip())
except json.JSONDecodeError as e:
    print(f"JSON parse error: {e}")
    Path(__file__).resolve().parent.joinpath("data", "v6_raw.txt").write_text(raw, encoding="utf-8")
    sys.exit(1)

output = Path(__file__).resolve().parent / "data" / "analysis_v6_20260401.json"
with open(output, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"done: {output}")
sections = [k for k in result.keys() if k.startswith("section")]
print(f"sections: {len(sections)}")
