"""Resend를 사용한 이메일 발송 모듈."""

import logging
import time

import resend

logger = logging.getLogger(__name__)


class ResendMailer:
    """Resend API로 커스텀 도메인 이메일을 발송한다."""

    def __init__(self, api_key: str, from_email: str = "report@interiordailyinsight.com"):
        resend.api_key = api_key
        self.from_email = from_email
        self.display_name = "Interior Daily Insight"

    def send(self, to_email: str, subject: str, html_content: str) -> bool:
        """단일 이메일 발송."""
        try:
            resend.Emails.send({
                "from": f"{self.display_name} <{self.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            })
            logger.info(f"이메일 발송 성공: {to_email}")
            return True
        except Exception as e:
            logger.error(f"이메일 발송 실패 ({to_email}): {e}")
            return False

    def send_batch(self, to_emails: list[str], subject: str, html_content: str) -> dict:
        """여러 명에게 발송."""
        success = 0
        failed = 0
        failed_list = []

        for email in to_emails:
            if self.send(email, subject, html_content):
                success += 1
            else:
                failed += 1
                failed_list.append(email)
            time.sleep(0.2)

        logger.info(f"일괄 발송 완료: 성공 {success}, 실패 {failed}")
        return {"success": success, "failed": failed, "failed_emails": failed_list}
