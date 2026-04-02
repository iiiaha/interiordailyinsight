"""네이버 SMTP를 사용한 이메일 발송 모듈."""

import logging
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

NAVER_SMTP_HOST = "smtp.naver.com"
NAVER_SMTP_PORT = 587


class NaverMailer:
    """네이버 SMTP로 이메일을 발송한다."""

    def __init__(self, naver_id: str, naver_pw: str, smtp_pw: str | None = None):
        self.email = f"{naver_id}@naver.com"
        self.password = smtp_pw or naver_pw  # 앱 비밀번호 우선
        self.display_name = "인테리어 인사이트 데일리"

    def send(self, to_email: str, subject: str, html_content: str) -> bool:
        """단일 이메일 발송."""
        msg = MIMEMultipart("alternative")
        msg["From"] = self.email
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText("HTML 이메일을 지원하는 클라이언트에서 확인해주세요.", "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            with smtplib.SMTP(NAVER_SMTP_HOST, NAVER_SMTP_PORT) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
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
            time.sleep(0.3)

        logger.info(f"일괄 발송 완료: 성공 {success}, 실패 {failed}")
        return {"success": success, "failed": failed, "failed_emails": failed_list}
