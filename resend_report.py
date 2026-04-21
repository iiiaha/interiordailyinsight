"""재발송 유틸리티 — 이미 생성된 report_YYYY-MM-DD.html 을 활성 구독자들에게 재발송.

사용:
    python resend_report.py                  # 오늘 리포트
    python resend_report.py 2026-04-21       # 특정 날짜
    TEST_MODE=1 python resend_report.py      # TEST_EMAIL 로만 발송
"""
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from mailer.resend_mailer import ResendMailer

date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
report_path = PROJECT_ROOT / "data" / f"report_{date}.html"

if not report_path.exists():
    print(f"리포트 파일 없음: {report_path}")
    sys.exit(1)

html = report_path.read_text(encoding="utf-8")

if os.getenv("TEST_MODE") == "1":
    test = os.getenv("TEST_EMAIL", "")
    emails = [e.strip() for e in test.split(",") if e.strip()]
    print(f"TEST_MODE → {emails}")
else:
    from supabase import create_client
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    response = sb.table("subscribers").select("email").eq("is_active", True).execute()
    emails = [s["email"] for s in (response.data or [])]
    print(f"활성 구독자: {len(emails)}명 → {emails}")

if not emails:
    print("발송 대상 없음 — 중단")
    sys.exit(0)

mailer = ResendMailer(api_key=os.getenv("RESEND_API_KEY"))
result = mailer.send_batch(
    emails,
    "[Interior Daily Insight] 오늘의 인사이트가 도착하였습니다",
    html,
)
print(f"결과: {result}")
