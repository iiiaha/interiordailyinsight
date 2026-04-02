"""Resend 이메일 발송 테스트."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import os
from mailer.resend_mailer import ResendMailer

# 리포트 로드
with open("data/report_v6_combined.html", "r", encoding="utf-8") as f:
    html = f.read()

mailer = ResendMailer(
    api_key=os.getenv("RESEND_API_KEY"),
    from_email="report@interiordailyinsight.com",
)

ok = mailer.send(
    to_email="iiiaha@naver.com",
    subject="[Interior Daily Insight] 오늘의 인사이트가 도착하였습니다",
    html_content=html,
)

if ok:
    print("success")
else:
    print("failed")
