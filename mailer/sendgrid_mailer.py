"""SendGrid를 사용한 이메일 발송 모듈."""

import logging
import time

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName, FileType, Disposition, ContentType,
)
import base64

from config.settings import SENDGRID_API_KEY, SENDGRID_FROM_EMAIL, SENDGRID_FROM_NAME

logger = logging.getLogger(__name__)


class SendGridMailer:
    """SendGrid를 통해 주간 리포트를 이메일로 발송한다."""

    def __init__(self):
        self.client = SendGridAPIClient(SENDGRID_API_KEY)

    def send_report(
        self,
        subscriber: dict,
        html_content: str,
        week_label: str,
        pdf_bytes: bytes | None = None,
    ) -> bool:
        """단일 구독자에게 리포트 이메일을 발송한다."""
        to_email = subscriber.get("email")
        subject = f"[인테리어 인사이트] {week_label} 주간 트렌드 보고서"

        message = Mail(
            from_email=(SENDGRID_FROM_EMAIL, SENDGRID_FROM_NAME),
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content="HTML 이메일을 지원하는 클라이언트에서 확인해주세요.",
        )

        # PDF 첨부 (선택)
        if pdf_bytes:
            encoded = base64.b64encode(pdf_bytes).decode()
            attachment = Attachment(
                FileContent(encoded),
                FileName(f"interior_insight_{week_label}.pdf"),
                FileType("application/pdf"),
                Disposition("attachment"),
            )
            message.attachment = attachment

        try:
            response = self.client.send(message)
            logger.info(f"이메일 발송 성공: {to_email} (상태: {response.status_code})")
            return True
        except Exception as e:
            logger.error(f"이메일 발송 실패: {to_email} - {e}")
            return False

    def send_batch(
        self,
        subscribers: list[dict],
        html_generator_fn,
        week_label: str,
        pdf_bytes: bytes | None = None,
    ) -> dict:
        """여러 구독자에게 개인화된 리포트를 일괄 발송한다."""
        success_count = 0
        failed_count = 0
        failed_emails: list[str] = []
        results: list[dict] = []

        for subscriber in subscribers:
            # 구독자별 개인화된 HTML 생성
            html_content = html_generator_fn(subscriber)

            ok = self.send_report(subscriber, html_content, week_label, pdf_bytes)
            if ok:
                success_count += 1
                results.append({"subscriber_id": subscriber["id"], "status": "success"})
            else:
                failed_count += 1
                failed_emails.append(subscriber.get("email", ""))
                results.append({"subscriber_id": subscriber["id"], "status": "failed"})

            # SendGrid rate limit 대응
            time.sleep(0.2)

        logger.info(f"일괄 발송 완료: 성공 {success_count}건, 실패 {failed_count}건")

        return {
            "success": success_count,
            "failed": failed_count,
            "failed_emails": failed_emails,
            "details": results,
        }
