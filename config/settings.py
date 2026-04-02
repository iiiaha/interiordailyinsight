"""환경 변수 및 서비스 설정 관리 모듈."""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _require(key: str) -> str:
    """필수 환경변수를 가져온다. 없으면 예외 발생."""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"필수 환경변수 '{key}'가 설정되지 않았습니다.")
    return value


# 네이버 검색 API
NAVER_CLIENT_ID = _require("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = _require("NAVER_CLIENT_SECRET")

# Claude API
ANTHROPIC_API_KEY = _require("ANTHROPIC_API_KEY")

# SendGrid
SENDGRID_API_KEY = _require("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "insight@yourdomain.com")
SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "인테리어 인사이트 위클리")

# Supabase
SUPABASE_URL = _require("SUPABASE_URL")
SUPABASE_KEY = _require("SUPABASE_KEY")

# 리포트 스케줄
REPORT_SEND_DAY = os.getenv("REPORT_SEND_DAY", "monday")
REPORT_SEND_HOUR = int(os.getenv("REPORT_SEND_HOUR", "9"))

# 서비스
SERVICE_DOMAIN = os.getenv("SERVICE_DOMAIN", "https://yourdomain.com")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# 수집 키워드
SEARCH_KEYWORDS = [
    "셀프인테리어",
    "인테리어 시공",
    "인테리어 업체",
    "집꾸미기",
    "인테리어 자재",
]

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).resolve().parent.parent
