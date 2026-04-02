"""Claude 분석기 테스트."""

import json
import pytest
from unittest.mock import patch, MagicMock


MOCK_ANALYSIS = {
    "executive_summary": "이번 주 모던 미니멀 인테리어 관심 급증",
    "hot_keywords": [
        {"keyword": "모던 미니멀", "count": 45, "trend": "상승", "insight": "30대 신혼부부 타겟 마케팅 강화 필요"}
    ],
    "style_trends": [
        {"style": "제패니즈 모던", "description": "일본식 미니멀", "business_opportunity": "우드톤 시공 패키지 제안"}
    ],
    "pain_points": [
        {"issue": "견적 불투명", "frequency": "높음", "recommended_action": "투명 견적 시스템 도입"}
    ],
    "material_brand_mentions": [
        {"name": "LX하우시스", "mention_count": 12, "sentiment": "긍정"}
    ],
    "weekly_opportunity": "봄 이사 시즌 대비 패키지 프로모션",
    "next_week_prediction": "화이트톤 인테리어 관심 지속 전망",
    "data_stats": {"total_posts": 150, "date_range": "2026-03-25 ~ 2026-04-01"},
}


@pytest.fixture
def mock_settings():
    with patch.dict("os.environ", {
        "NAVER_CLIENT_ID": "test_id",
        "NAVER_CLIENT_SECRET": "test_secret",
        "ANTHROPIC_API_KEY": "test_key",
        "SENDGRID_API_KEY": "test_sg",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_key",
    }):
        yield


def test_analyze_success(mock_settings):
    """정상적인 분석 결과 파싱을 확인한다."""
    from analyzer.claude_analyzer import ClaudeAnalyzer

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(MOCK_ANALYSIS, ensure_ascii=False))]

    with patch("analyzer.claude_analyzer.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = mock_message
        analyzer = ClaudeAnalyzer()
        result = analyzer.analyze("테스트 데이터", "2026-03-25", "2026-04-01", 150)

    assert "executive_summary" in result
    assert "hot_keywords" in result
    assert "pain_points" in result
    assert "weekly_opportunity" in result
    assert len(result["hot_keywords"]) > 0


def test_analyze_json_in_code_block(mock_settings):
    """```json 블록 안의 JSON도 파싱 가능한지 확인한다."""
    from analyzer.claude_analyzer import ClaudeAnalyzer

    wrapped = f"```json\n{json.dumps(MOCK_ANALYSIS, ensure_ascii=False)}\n```"
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=wrapped)]

    with patch("analyzer.claude_analyzer.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = mock_message
        analyzer = ClaudeAnalyzer()
        result = analyzer.analyze("테스트 데이터", "2026-03-25", "2026-04-01", 150)

    assert "executive_summary" in result


def test_analyze_required_keys(mock_settings):
    """필수 키 누락 시에도 결과를 반환하는지 확인한다."""
    from analyzer.claude_analyzer import ClaudeAnalyzer

    partial = {"executive_summary": "요약만 있음"}
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(partial))]

    with patch("analyzer.claude_analyzer.anthropic.Anthropic") as MockClient:
        MockClient.return_value.messages.create.return_value = mock_message
        analyzer = ClaudeAnalyzer()
        result = analyzer.analyze("테스트", "2026-03-25", "2026-04-01")

    # 누락된 키가 있어도 결과는 반환
    assert "executive_summary" in result
