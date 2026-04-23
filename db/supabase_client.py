"""Supabase 데이터베이스 클라이언트 래퍼."""

import logging
import os
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Supabase DB 작업을 위한 래퍼 클래스. service_role 키로 RLS 우회.

    config.settings 대신 env 를 직접 읽음 — 이 모듈만 단독으로 쓸 수 있도록
    (NAVER_CLIENT_ID 등 수집 관련 필수 env 가 없는 환경에서도 동작).
    """

    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise EnvironmentError("SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY 미설정")
        self.client: Client = create_client(url, key)
        logger.info("Supabase 클라이언트 초기화 완료")

    def get_active_subscribers(self) -> list[dict]:
        """활성 구독자 목록을 조회한다."""
        response = (
            self.client.table("subscribers")
            .select("*")
            .eq("is_active", True)
            .execute()
        )
        subscribers = response.data or []
        logger.info(f"활성 구독자 {len(subscribers)}명 조회 완료")
        return subscribers

    def save_report(self, report_data: dict) -> str:
        """주간 리포트를 저장하고 ID를 반환한다."""
        response = (
            self.client.table("weekly_reports")
            .insert(report_data)
            .execute()
        )
        report_id = response.data[0]["id"]
        logger.info(f"리포트 저장 완료: {report_id}")
        return report_id

    def update_report_sent(self, report_id: str, count: int):
        """리포트 발송 완료 상태를 업데이트한다."""
        from datetime import datetime, timezone

        self.client.table("weekly_reports").update({
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "recipient_count": count,
        }).eq("id", report_id).execute()
        logger.info(f"리포트 발송 상태 업데이트: {report_id}, 수신자 {count}명")

    def log_send(self, report_id: str, subscriber_id: str, status: str, error_message: Optional[str] = None):
        """개별 발송 로그를 기록한다."""
        self.client.table("send_logs").insert({
            "report_id": report_id,
            "subscriber_id": subscriber_id,
            "status": status,
            "error_message": error_message,
        }).execute()

    def log_collection(self, keyword: str, post_count: int, status: str, error_message: Optional[str] = None):
        """수집 로그를 기록한다."""
        self.client.table("collection_logs").insert({
            "keyword": keyword,
            "post_count": post_count,
            "status": status,
            "error_message": error_message,
        }).execute()

    def add_subscriber(self, email: str, name: Optional[str] = None, company: Optional[str] = None, plan: str = "basic") -> dict:
        """구독자를 추가한다."""
        response = self.client.table("subscribers").insert({
            "email": email,
            "name": name,
            "company": company,
            "plan": plan,
        }).execute()
        logger.info(f"구독자 추가: {email}")
        return response.data[0]

    def deactivate_subscriber(self, subscriber_id: str):
        """구독자를 비활성화한다 (구독 해지)."""
        self.client.table("subscribers").update({
            "is_active": False,
        }).eq("id", subscriber_id).execute()
        logger.info(f"구독자 비활성화: {subscriber_id}")
