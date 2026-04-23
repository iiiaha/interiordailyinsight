"""네이버 게시글 수집기 테스트."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta


@pytest.fixture
def mock_settings():
    """설정 모킹."""
    with patch.dict("os.environ", {
        "NAVER_CLIENT_ID": "test_id",
        "NAVER_CLIENT_SECRET": "test_secret",
        "ANTHROPIC_API_KEY": "test_key",
        "SENDGRID_API_KEY": "test_sg",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_key",
        "SUPABASE_SERVICE_ROLE_KEY": "test_service_key",
    }):
        yield


def _make_item(title: str, link: str, days_ago: int = 1) -> dict:
    """테스트용 네이버 API 응답 아이템을 생성한다."""
    pub_date = (datetime.now(timezone.utc) - timedelta(days=days_ago))
    return {
        "title": f"<b>{title}</b>",
        "description": f"<b>{title}</b> 관련 상세 설명 텍스트입니다.",
        "link": link,
        "pubDate": pub_date.strftime("%a, %d %b %Y %H:%M:%S %z"),
        "cafename": "셀프인테리어",
    }


def test_date_filtering(mock_settings):
    """날짜 필터링이 정상 동작하는지 확인한다."""
    from collector.naver_collector import NaverCollector

    collector = NaverCollector()

    # 3일 전 게시글 - 7일 이내이므로 True
    assert collector._is_within_days(
        _make_item("test", "link", days_ago=3)["pubDate"], 7
    ) is True

    # 10일 전 게시글 - 7일 초과이므로 False
    assert collector._is_within_days(
        _make_item("test", "link", days_ago=10)["pubDate"], 7
    ) is False


def test_deduplication(mock_settings):
    """중복 링크 제거가 정상 동작하는지 확인한다."""
    from collector.naver_collector import NaverCollector

    collector = NaverCollector()

    items = [
        _make_item("게시글1", "https://cafe.naver.com/1", days_ago=1),
        _make_item("게시글2", "https://cafe.naver.com/1", days_ago=1),  # 중복
        _make_item("게시글3", "https://cafe.naver.com/2", days_ago=1),
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": items, "total": 3}
    mock_response.raise_for_status = MagicMock()

    with patch.object(collector.session, "get", return_value=mock_response):
        posts = collector.collect_weekly_posts(keywords=["테스트"], days_back=7)

    # 중복 제거 후 2건
    assert len(posts) == 2


def test_empty_response(mock_settings):
    """빈 응답 처리를 확인한다."""
    from collector.naver_collector import NaverCollector

    collector = NaverCollector()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [], "total": 0}
    mock_response.raise_for_status = MagicMock()

    with patch.object(collector.session, "get", return_value=mock_response):
        posts = collector.collect_weekly_posts(keywords=["테스트"], days_back=7)

    assert len(posts) == 0
