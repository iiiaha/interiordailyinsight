"""유튜브 데일리 분석 테스트."""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import anthropic
from config.settings import ANTHROPIC_API_KEY

# 1. 데이터 로드 — 오늘(4/2) + 어제(4/1) 영상만 (테스트용)
data_file = Path(__file__).resolve().parent / "data" / "youtube_2026-04-02.json"
with open(data_file, "r", encoding="utf-8") as f:
    all_videos = json.load(f)

# 자막 있는 것만, 최근 2일
videos = [v for v in all_videos if v.get("has_transcript") and v["published"][:10] >= "2026-04-01"]
print(f"total: {len(all_videos)}, filtered: {len(videos)}")

# 2. 분석용 텍스트 구성
lines = []
for i, v in enumerate(videos):
    transcript = v.get("transcript", "")[:2000]  # 자막 최대 2000자
    if len(v.get("transcript", "")) > 2000:
        transcript += "..."
    lines.append(f"\n--- [video_id: {v['video_id']}] {v['channel']} ---")
    lines.append(f"제목: {v['title']}")
    lines.append(f"자막: {transcript}")

aggregated = "\n".join(lines)
print(f"analysis text: {len(aggregated):,} chars")

# 3. 프롬프트
SYSTEM_PROMPT = """당신은 인테리어 업계 비즈니스 인텔리전스 애널리스트입니다.
유튜브 인테리어 전문 채널의 영상을 분석하여, 시공업체와 디자이너에게 실무적 인사이트를 제공합니다.

톤: 전문 컨설턴트가 고액 고객에게 보고하는 격식 있는 존댓말.
원칙:
- 각 영상의 핵심 내용을 2~3문장으로 요약하십시오.
- 영상에서 언급된 구체적 제품명, 시공법, 가격은 반드시 포함하십시오.
- 전체 영상을 종합하여 사업자에게 실행 가능한 인사이트를 제공하십시오.
응답: 순수 JSON만."""

USER_PROMPT = f"""아래는 오늘 업로드된 인테리어 유튜브 영상 {len(videos)}건의 자막입니다.

{aggregated}

---

다음 JSON을 작성하십시오.

{{
  "featured_videos": [
    {{
      "video_id": "위 데이터에서 제공된 video_id를 그대로 사용",
      "channel": "채널명",
      "title": "영상 제목",
      "summary": "영상 핵심 내용 2~3문장 요약. 언급된 제품명, 시공법, 가격 포함.",
      "business_value": "이 영상이 업체에게 왜 중요한지 1줄",
      "keywords": ["영상에서 언급된 특정 제품명만 추출. 브랜드+모델명 조합만 해당. 예: '나노드론 공기청정기', '사바 이탈리아 소파', '리페르 냉장고', '삼성 비스포크', 'LX하우시스 인테리어필름'. '아일랜드', '급배수', '수납' 같은 일반 명사는 절대 포함하지 마십시오. 구매 가능한 특정 상품명만. 없으면 빈 배열."]
    }}
  ],
  "overall_insight": {{
    "title": "오늘의 유튜브 종합 인사이트",
    "insight": "오늘 영상들을 전체적으로 종합했을 때 사업자가 알아야 할 핵심 메시지 2~3문장. 존댓말.",
    "action": "이 인사이트를 바탕으로 업체가 취해야 할 행동 1줄. 존댓말."
  }}
}}"""

# 4. Claude 분석
print("\nClaude analysis...")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4000,
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

output = Path(__file__).resolve().parent / "data" / "youtube_analysis_20260402.json"
with open(output, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"done: {output}")
print(f"featured videos: {len(result.get('featured_videos', []))}")
