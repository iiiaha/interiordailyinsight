"""v4: 업자 관점 5섹션 구조 분석."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import anthropic
from config.settings import ANTHROPIC_API_KEY

# 1. 풀 데이터 로드
data_file = Path(__file__).resolve().parent / "data" / "crawl_full_20260401.json"
with open(data_file, "r", encoding="utf-8") as f:
    posts = json.load(f)

print(f"총 {len(posts)}건 로드")

# 2. 분석용 텍스트 구성
groups: dict[str, list[dict]] = {}
for p in posts:
    board = p.get("board", "기타")
    groups.setdefault(board, []).append(p)

lines = []
char_count = 0
MAX_CHARS = 90000

for board, board_posts in sorted(groups.items(), key=lambda x: -len(x[1])):
    lines.append(f"\n===== [게시판: {board}] ({len(board_posts)}건) =====")
    for p in board_posts:
        content = p.get("content", "")[:300]
        if len(p.get("content", "")) > 300:
            content += "..."
        comments = p.get("comments", [])
        comment_text = ""
        if comments:
            comment_text = " | ".join(c[:100] for c in comments[:5])

        entry = f"\n[제목] {p.get('title', '')}"
        if content:
            entry += f"\n[본문] {content}"
        if comment_text:
            entry += f"\n[댓글] {comment_text}"

        if char_count + len(entry) > MAX_CHARS:
            lines.append("\n... (이하 생략)")
            break
        lines.append(entry)
        char_count += len(entry)
    else:
        continue
    break

aggregated = "\n".join(lines)
print(f"분석용 텍스트: {len(aggregated):,}자")

# 3. 프롬프트
SYSTEM_PROMPT = """당신은 인테리어 시공업체와 디자이너를 위한 비즈니스 인텔리전스 애널리스트입니다.

독자: 1~5명 규모 소형 인테리어 업체 대표, 프리랜서 디자이너
이들은 바쁘다. 30초 안에 핵심을 파악하고, 오늘 영업에 바로 써먹을 수 있어야 한다.

원칙:
- 데이터에서 직접 추출한 구체적 키워드, 가격, 브랜드, 자재명만 사용한다
- "트렌드가 있습니다" 같은 추상적 표현 대신 "디아망 벽지 언급 23회, 주로 색상 고민" 같은 구체적 표현
- 모든 분석은 "업체가 어떻게 써먹는가"로 마무리
- 과장 금지. 데이터에 없는 건 추측이라고 명시

응답: 순수 JSON만 반환. 코드블록, 설명 텍스트 없이."""

USER_PROMPT = f"""아래는 2026-04-01 하루 동안 네이버 '셀프인테리어' 카페에서 수집된
게시글 {len(posts)}개의 제목, 본문, 댓글입니다.

[수집 데이터]
{aggregated}

---

위 데이터를 분석하여 다음 JSON을 작성하세요.

{{
  "meta": {{
    "date": "2026-04-01",
    "total_posts": {len(posts)},
    "generated_at": "{datetime.now().strftime('%Y-%m-%d %H:%M')}",
    "data_note": "데이터 한계 한 문장 (없으면 null)"
  }},

  "section1_hot_keywords": {{
    "title": "오늘의 핫 키워드 TOP 10",
    "description": "오늘 소비자들 사이에서 가장 많이 언급된 키워드. 업체가 시장 온도를 한눈에 파악하는 용도.",
    "keywords": [
      {{
        "rank": 1,
        "keyword": "키워드",
        "mention_count": "게시글+댓글에서 해당 키워드/주제가 언급된 횟수 (숫자)",
        "heat": "🔥🔥🔥|🔥🔥|🔥",
        "why_hot": "왜 뜨고 있는지 한 줄 (데이터 기반)",
        "business_read": "업체가 이 키워드를 보고 해야 할 생각 한 줄"
      }}
    ]
  }},

  "section2_consumer_questions": {{
    "title": "소비자가 가장 궁금해하는 것 TOP 5",
    "description": "소비자들이 반복적으로 묻는 질문. 상담 때 먼저 답해주면 신뢰 확보 가능.",
    "questions": [
      {{
        "rank": 1,
        "question": "소비자들이 반복적으로 묻는 질문 (원문 뉘앙스 반영)",
        "frequency": "높음|중간",
        "example_post": "실제 게시글 제목이나 본문에서 발췌한 예시 1개",
        "expert_answer_hint": "업체가 상담 때 이렇게 답하면 신뢰를 얻는다 (구체적 대답 가이드)",
        "sales_angle": "이 질문을 받았을 때 자연스럽게 계약으로 연결하는 화법"
      }}
    ]
  }},

  "section3_consumer_wants": {{
    "title": "소비자가 가장 원하는 것 TOP 5",
    "description": "소비자들이 반복적으로 원하는 것. 내 서비스의 셀링포인트로 삼아야 할 것들.",
    "wants": [
      {{
        "rank": 1,
        "want": "소비자가 원하는 것 (구체적으로)",
        "intensity": "강함|보통",
        "evidence": "이걸 원한다는 근거 (게시글/댓글에서 추출)",
        "how_to_sell": "이 욕구를 내 서비스 소구포인트로 만드는 방법",
        "package_idea": "이 욕구를 패키지 상품으로 만든다면 어떤 형태가 좋을지"
      }}
    ]
  }},

  "section4_one_action": {{
    "title": "오늘의 액션 한 줄",
    "action": "위 3개 섹션을 종합해서, 오늘 업체가 딱 하나만 한다면 이것 (구체적 행동)",
    "why": "왜 오늘 이걸 해야 하는지 (데이터 근거)",
    "how": "어떻게 하는지 (3단계 이내)"
  }},

  "section5_raw_voices": {{
    "title": "오늘의 소비자 생목소리",
    "description": "업자가 읽으면 현장 감각이 살아나는 실제 소비자 발언",
    "voices": [
      {{
        "quote": "소비자 실제 발언 (본문 또는 댓글에서 인용, 원문 뉘앙스 최대한 유지)",
        "context": "어떤 상황에서 나온 말인지 한 줄",
        "takeaway": "업자가 이 말에서 읽어야 할 시그널"
      }}
    ]
  }}
}}"""

# 4. Claude 분석
print("\nClaude 분석 요청 중...")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=6000,
    system=SYSTEM_PROMPT,
    messages=[{"role": "user", "content": USER_PROMPT}],
)

raw = message.content[0].text
print(f"응답: {len(raw):,}자")

try:
    text = raw.strip()
    if "```json" in text:
        text = text[text.index("```json")+7:text.index("```", text.index("```json")+7)]
    elif "```" in text:
        text = text[text.index("```")+3:text.index("```", text.index("```")+3)]
    result = json.loads(text.strip())
except json.JSONDecodeError as e:
    print(f"JSON 파싱 실패: {e}")
    with open(Path(__file__).resolve().parent / "data" / "v4_raw.txt", "w", encoding="utf-8") as f:
        f.write(raw)
    sys.exit(1)

output = Path(__file__).resolve().parent / "data" / "analysis_v4_20260401.json"
with open(output, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"완료: {output}")
