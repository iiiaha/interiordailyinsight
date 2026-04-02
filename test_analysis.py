"""수집된 제목 데이터로 Claude 분석 테스트."""

import json
import sys
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
# 12000자 제한
if len(aggregated) > 12000:
    aggregated = aggregated[:12000] + "\n\n... (이하 생략)"

print(f"분석용 텍스트: {len(aggregated)}자")

# 4. Claude 분석
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

system_prompt = """당신은 인테리어 업계 전문 트렌드 애널리스트입니다.
인테리어 디자이너와 인테리어 시공 업체를 위한 주간 인사이트 보고서를 작성합니다.
분석은 항상 비즈니스 관점에서 실용적이고 구체적이어야 합니다.
인테리어 디자이너가 영업이나 설계에 바로 활용할 수 있는 비즈니스 인사이트 위주로 추출하세요.
반드시 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 포함하지 마세요."""

user_prompt = f"""아래는 2026년 4월 1일 네이버 '셀프인테리어' 카페에서 수집된 {len(posts)}개의 게시글 제목입니다.
인테리어 업체와 디자이너를 위한 인사이트를 분석해주세요.

[수집 데이터]
{aggregated}

다음 JSON 구조로 분석 결과를 반환하세요:
{{
  "executive_summary": "오늘의 핵심 트렌드 2-3문장 요약",
  "hot_keywords": [
    {{"keyword": "키워드", "count": 숫자, "trend": "상승|유지|하락", "insight": "업체를 위한 한줄 인사이트"}}
  ],
  "style_trends": [
    {{"style": "스타일명", "description": "설명", "business_opportunity": "영업 기회"}}
  ],
  "pain_points": [
    {{"issue": "소비자 불만/질문", "frequency": "높음|중간|낮음", "recommended_action": "업체 대응 방안"}}
  ],
  "material_brand_mentions": [
    {{"name": "자재 또는 브랜드명", "mention_count": 숫자, "sentiment": "긍정|중립|부정"}}
  ],
  "weekly_opportunity": "오늘 인테리어 업체가 놓치면 안 될 영업 기회 1가지 (구체적으로)",
  "next_week_prediction": "다음 주 예상 트렌드 1-2문장",
  "data_stats": {{
    "total_posts": {len(posts)},
    "date_range": "2026-04-01"
  }}
}}"""

print("\nClaude 분석 요청 중...")
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4000,
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
)

raw = message.content[0].text
print(f"\n응답 길이: {len(raw)}자")

# JSON 파싱
try:
    if "```json" in raw:
        start = raw.index("```json") + 7
        end = raw.index("```", start)
        raw = raw[start:end]
    result = json.loads(raw.strip())
except json.JSONDecodeError as e:
    print(f"JSON 파싱 실패: {e}")
    print(f"원본 응답:\n{raw[:500]}")
    sys.exit(1)

# 결과 저장
output_file = Path(__file__).resolve().parent / "data" / "analysis_20260401.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# 결과 출력
print("\n" + "=" * 60)
print("분석 결과")
print("=" * 60)

print(f"\n[요약]\n{result.get('executive_summary', '')}")

print(f"\n[핫 키워드]")
for kw in result.get("hot_keywords", []):
    arrow = {"상승": "↑", "하락": "↓", "유지": "→"}.get(kw.get("trend", ""), "")
    print(f"  {arrow} {kw['keyword']} ({kw.get('count', '')}회) - {kw.get('insight', '')}")

print(f"\n[스타일 트렌드]")
for s in result.get("style_trends", []):
    print(f"  {s['style']}: {s.get('description', '')}")
    print(f"    -> 영업 기회: {s.get('business_opportunity', '')}")

print(f"\n[소비자 페인포인트]")
for pp in result.get("pain_points", []):
    print(f"  [{pp.get('frequency', '')}] {pp['issue']}")
    print(f"    -> 대응: {pp.get('recommended_action', '')}")

print(f"\n[자재/브랜드 언급]")
for mb in result.get("material_brand_mentions", []):
    print(f"  {mb['name']} ({mb.get('mention_count', '')}회, {mb.get('sentiment', '')})")

print(f"\n[오늘의 영업 기회]\n  {result.get('weekly_opportunity', '')}")
print(f"\n[다음 주 예측]\n  {result.get('next_week_prediction', '')}")

print(f"\n분석 결과 저장: {output_file}")
