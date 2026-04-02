"""Claude API를 사용한 인테리어 트렌드 분석 모듈."""

import json
import logging

import anthropic

from config.settings import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 인테리어 업계 전문 트렌드 애널리스트입니다.
인테리어 디자이너와 인테리어 시공 업체를 위한 주간 인사이트 보고서를 작성합니다.
분석은 항상 비즈니스 관점에서 실용적이고 구체적이어야 합니다.
인테리어 디자이너가 영업이나 설계에 바로 활용할 수 있는 비즈니스 인사이트 위주로 추출하세요.
반드시 아래 JSON 형식으로만 응답하세요. JSON 외의 텍스트는 포함하지 마세요."""

USER_PROMPT_TEMPLATE = """아래는 {week_start} ~ {week_end} 네이버 인테리어 커뮤니티에서 수집된 {count}개의 게시글입니다.
인테리어 업체와 디자이너를 위한 주간 인사이트를 분석해주세요.

[수집 데이터]
{aggregated_text}

다음 JSON 구조로 분석 결과를 반환하세요:
{{
  "executive_summary": "이번 주 핵심 트렌드 2-3문장 요약",
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
  "weekly_opportunity": "이번 주 인테리어 업체가 놓치면 안 될 영업 기회 1가지 (구체적으로)",
  "next_week_prediction": "다음 주 예상 트렌드 1-2문장",
  "data_stats": {{
    "total_posts": 숫자,
    "date_range": "{week_start} ~ {week_end}"
  }}
}}"""


class ClaudeAnalyzer:
    """Claude API를 사용하여 수집된 게시글을 분석한다."""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def _call_claude(self, aggregated_text: str, week_start: str, week_end: str, post_count: int) -> str:
        """Claude API를 호출하여 분석 결과를 받는다."""
        user_prompt = USER_PROMPT_TEMPLATE.format(
            week_start=week_start,
            week_end=week_end,
            count=post_count,
            aggregated_text=aggregated_text,
        )

        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return message.content[0].text

    def _parse_json(self, text: str) -> dict:
        """응답에서 JSON을 추출하여 파싱한다."""
        # JSON 블록이 ```json ... ``` 안에 있을 수 있음
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end]
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            text = text[start:end]

        return json.loads(text.strip())

    def analyze(self, aggregated_text: str, week_start: str, week_end: str, post_count: int = 0) -> dict:
        """수집 데이터를 분석하여 인사이트를 생성한다. JSON 파싱 실패 시 1회 재시도."""
        for attempt in range(2):
            try:
                raw_response = self._call_claude(aggregated_text, week_start, week_end, post_count)
                result = self._parse_json(raw_response)

                # 필수 키 검증
                required_keys = [
                    "executive_summary", "hot_keywords", "style_trends",
                    "pain_points", "weekly_opportunity",
                ]
                missing = [k for k in required_keys if k not in result]
                if missing:
                    logger.warning(f"분석 결과에 누락된 키: {missing}")

                logger.info("AI 분석 완료")
                return result

            except json.JSONDecodeError as e:
                if attempt == 0:
                    logger.warning(f"JSON 파싱 실패, 재시도합니다: {e}")
                    continue
                logger.error(f"JSON 파싱 최종 실패: {e}")
                return {"error": str(e), "raw_response": raw_response}

            except anthropic.APIError as e:
                logger.error(f"Claude API 호출 실패: {e}")
                return {"error": str(e)}

        return {"error": "분석 실패 - 최대 재시도 횟수 초과"}
