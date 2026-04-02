"""v5: 키워드 카운팅은 코드, 해석은 Claude."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import anthropic
from config.settings import ANTHROPIC_API_KEY
from processor.keyword_counter import count_keywords, get_keyword_summary

# 1. 데이터 로드
data_file = Path(__file__).resolve().parent / "data" / "crawl_full_20260401.json"
with open(data_file, "r", encoding="utf-8") as f:
    posts = json.load(f)

print(f"총 {len(posts)}건 로드")

# 2. 코드 기반 키워드 카운팅
keyword_ranking = count_keywords(posts)
keyword_summary = get_keyword_summary(posts)
print(f"keyword counting done: {len(keyword_ranking)} keywords")

# 3. 분석용 텍스트 (본문+댓글)
groups: dict[str, list[dict]] = {}
for p in posts:
    groups.setdefault(p.get("board", "기타"), []).append(p)

lines = []
char_count = 0
MAX_CHARS = 80000  # 키워드 요약이 추가되니 조금 줄임

for board, bposts in sorted(groups.items(), key=lambda x: -len(x[1])):
    lines.append(f"\n===== [게시판: {board}] ({len(bposts)}건) =====")
    for p in bposts:
        content = p.get("content", "")[:300]
        if len(p.get("content", "")) > 300:
            content += "..."
        comments = " | ".join(c[:100] for c in p.get("comments", [])[:5])
        entry = f"\n[제목] {p['title']}"
        if content:
            entry += f"\n[본문] {content}"
        if comments:
            entry += f"\n[댓글] {comments}"
        if char_count + len(entry) > MAX_CHARS:
            break
        lines.append(entry)
        char_count += len(entry)
    else:
        continue
    break

aggregated = "\n".join(lines)
print(f"분석용 텍스트: {len(aggregated):,}자")

# 4. 프롬프트
SYSTEM_PROMPT = """당신은 연간 수천만 원의 컨설팅 피를 받는 인테리어 업계 전문 비즈니스 인텔리전스 애널리스트입니다.

독자: 1~5명 규모 소형 인테리어 시공업체 대표, 프리랜서 인테리어 디자이너.

톤앤매너 (매우 중요):
- 전문 컨설턴트가 고액 고객에게 보고하는 어조. 격식 있는 존댓말을 사용하세요.
- "~하자", "~해라", "~하면 됨" 금지. 반드시 "~하십시오", "~하시기 바랍니다", "~을 권장합니다" 식으로.
- 냉철하고 분석적이되, 읽는 사람이 "돈 내고 볼 만하다"고 느끼는 전문성을 보여주세요.

원칙:
- 키워드 순위와 언급 횟수는 코드로 정확히 계산되어 제공됩니다. 이 숫자를 그대로 사용하십시오.
- 당신의 역할은 숫자를 세는 것이 아니라, 왜 이 키워드가 뜨는지 해석하고 액션을 제안하는 것입니다.
- 구체적 가격, 브랜드, 자재명을 본문/댓글에서 추출하십시오.
- 모든 분석은 "그래서 업체는 무엇을 해야 하는가"로 마무리하십시오.

소비자 생목소리 섹션 (section5) 주의사항:
- 원문을 절대 그대로 인용하지 마십시오. 저작권 이슈가 있습니다.
- 반드시 의미를 재구성하여 "~라는 취지의 의견이 다수 확인되었습니다" 식으로 작성하십시오.
- 소비자의 감정과 의도는 살리되, 문장 자체는 완전히 새로 작성하십시오.

응답: 순수 JSON만. 코드블록 없이."""

# 키워드 TOP 10을 JSON 구조로 미리 만듦
keyword_top10 = keyword_ranking[:10]
keyword_json_hint = json.dumps(keyword_top10, ensure_ascii=False)

USER_PROMPT = f"""아래는 2026-04-01 하루 동안 네이버 '셀프인테리어' 카페에서 수집된 {len(posts)}개의 게시글입니다.

[코드 기반 키워드 카운팅 결과 — 이 숫자를 그대로 사용하세요]
{keyword_summary}

[수집 원문 데이터]
{aggregated}

---

다음 JSON을 작성하세요.

section1_hot_keywords의 keywords는 반드시 아래 코드 카운팅 결과를 그대로 사용하고,
why_hot과 business_read만 본문/댓글을 분석하여 작성하세요:
{keyword_json_hint}

{{
  "meta": {{"date": "2026-04-01", "total_posts": {len(posts)}, "generated_at": "{datetime.now().strftime('%Y-%m-%d %H:%M')}", "data_note": null}},

  "section1_hot_keywords": {{
    "title": "오늘의 핫 키워드 TOP 10",
    "description": "코드 기반 정확 카운팅. 게시글+본문+댓글에서 키워드가 등장한 게시글 수.",
    "keywords": [
      {{
        "rank": "위 카운팅 결과 그대로",
        "keyword": "위 카운팅 결과 그대로",
        "mention_count": "위 카운팅 결과 숫자 그대로",
        "heat": "위 카운팅 결과 그대로",
        "why_hot": "본문/댓글을 분석하여 왜 이 키워드가 뜨는지 한 줄",
        "business_read": "업체가 이걸 보고 해야 할 생각 한 줄"
      }}
    ]
  }},

  "section2_consumer_questions": {{
    "title": "오늘 소비자가 가장 궁금해하는 것 TOP 5",
    "description": "오늘 커뮤니티에서 반복된 질문. 상담 때 먼저 답하면 신뢰 확보.",
    "questions": [
      {{
        "rank": 1,
        "question": "질문 (원문 뉘앙스 반영)",
        "frequency": "높음|중간",
        "example_post": "실제 게시글 예시",
        "expert_answer_hint": "답변 가이드",
        "sales_angle": "세일즈 화법"
      }}
    ]
  }},

  "section3_consumer_wants": {{
    "title": "오늘 소비자가 가장 원하는 것 TOP 5",
    "description": "오늘 데이터 기반, 내 서비스의 셀링포인트로 삼아야 할 것들.",
    "wants": [
      {{
        "rank": 1,
        "want": "원하는 것",
        "intensity": "강함|보통",
        "evidence": "근거 (본문/댓글 기반)",
        "how_to_sell": "소구포인트",
        "package_idea": "패키지 아이디어"
      }}
    ]
  }},

  "section4_one_action": {{
    "title": "오늘의 액션 한 줄",
    "action": "구체적 행동",
    "why": "이유 (데이터 근거)",
    "how": "실행법 (3단계 이내)"
  }},

  "section5_raw_voices": {{
    "title": "금일 주목할 소비자 시그널",
    "description": "커뮤니티에서 포착된 주요 소비자 동향을 재구성하여 전달합니다.",
    "voices": [
      {{
        "quote": "원문을 절대 그대로 옮기지 마십시오. 반드시 완전히 새로운 문장으로 재구성하십시오. 예시: '필름 시공 후 도배지 접착 불량에 대해 업체 측의 무책임한 태도에 불만을 표하는 소비자가 다수 확인되었습니다' 식으로 분석가가 요약 보고하는 형태로 작성.",
        "context": "해당 시그널이 발생한 배경",
        "takeaway": "이 시그널에 대응하여 업체가 취해야 할 조치를 권장합니다 (존댓말)"
      }}
    ]
  }}
}}"""

# 5. Claude 분석
print("\nClaude 분석 요청 중...")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=6000,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": USER_PROMPT}],
)

raw = message.content[0].text
text = raw.strip()
if "```json" in text:
    text = text[text.index("```json")+7:text.index("```", text.index("```json")+7)]
elif "```" in text:
    text = text[text.index("```")+3:text.index("```", text.index("```")+3)]

result = json.loads(text.strip())

output = Path(__file__).resolve().parent / "data" / "analysis_v5_20260401.json"
with open(output, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"완료: {output}")

# 키워드 순위 검증
kws = result.get("section1_hot_keywords", {}).get("keywords", [])
print("keyword top5 check:")
for k in kws[:5]:
    print(f"  {k['rank']}. {k['keyword']} {k['mention_count']}")
