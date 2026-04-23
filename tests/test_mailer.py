"""SendGrid 이메일 발송 테스트."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_settings():
    with patch.dict("os.environ", {
        "NAVER_CLIENT_ID": "test_id",
        "NAVER_CLIENT_SECRET": "test_secret",
        "ANTHROPIC_API_KEY": "test_key",
        "SENDGRID_API_KEY": "test_sg",
        "SENDGRID_FROM_EMAIL": "test@test.com",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test_key",
        "SUPABASE_SERVICE_ROLE_KEY": "test_service_key",
    }):
        yield


def test_send_report_success(mock_settings):
    """단일 발송 성공을 확인한다."""
    from mailer.sendgrid_mailer import SendGridMailer

    mock_response = MagicMock()
    mock_response.status_code = 202

    with patch("mailer.sendgrid_mailer.SendGridAPIClient") as MockSG:
        MockSG.return_value.send.return_value = mock_response
        mailer = SendGridMailer()
        result = mailer.send_report(
            subscriber={"id": "test-id", "email": "user@test.com", "name": "테스터"},
            html_content="<h1>테스트</h1>",
            week_label="2026-03-25~2026-04-01",
        )

    assert result is True


def test_send_report_failure(mock_settings):
    """발송 실패 시 False 반환을 확인한다."""
    from mailer.sendgrid_mailer import SendGridMailer

    with patch("mailer.sendgrid_mailer.SendGridAPIClient") as MockSG:
        MockSG.return_value.send.side_effect = Exception("API 오류")
        mailer = SendGridMailer()
        result = mailer.send_report(
            subscriber={"id": "test-id", "email": "user@test.com"},
            html_content="<h1>테스트</h1>",
            week_label="2026-03-25~2026-04-01",
        )

    assert result is False


def test_send_batch(mock_settings):
    """일괄 발송 결과를 확인한다."""
    from mailer.sendgrid_mailer import SendGridMailer

    mock_response = MagicMock()
    mock_response.status_code = 202

    subscribers = [
        {"id": "id-1", "email": "a@test.com", "name": "김철수"},
        {"id": "id-2", "email": "b@test.com", "name": "이영희"},
        {"id": "id-3", "email": "c@test.com", "name": "박민수"},
    ]

    with patch("mailer.sendgrid_mailer.SendGridAPIClient") as MockSG:
        MockSG.return_value.send.return_value = mock_response
        mailer = SendGridMailer()
        result = mailer.send_batch(
            subscribers=subscribers,
            html_generator_fn=lambda sub: f"<h1>{sub['name']}</h1>",
            week_label="2026-03-25~2026-04-01",
        )

    assert result["success"] == 3
    assert result["failed"] == 0
