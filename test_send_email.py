"""네이버 SMTP 이메일 발송 테스트."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

import os
from mailer.naver_mailer import NaverMailer

# 아까 생성한 리포트 로드
report_file = Path(__file__).resolve().parent / "data" / "report_v6_combined.html"
with open(report_file, "r", encoding="utf-8") as f:
    html = f.read()

mailer = NaverMailer(
    naver_id=os.getenv("NAVER_ID"),
    naver_pw=os.getenv("NAVER_PW"),
    smtp_pw=os.getenv("NAVER_SMTP_PW"),
)

ok = mailer.send(
    to_email="iiiaha@naver.com",
    subject="[Interior Daily Insight] 오늘의 인사이트가 도착하였습니다",
    html_content=html,
)

if ok:
    print("발송 성공! 메일함 확인해봐.")
else:
    print("발송 실패.")
