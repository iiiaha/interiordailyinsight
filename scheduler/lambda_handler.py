"""주간 리포트 파이프라인 메인 핸들러.

AWS Lambda 또는 로컬에서 실행 가능.
전체 파이프라인: 수집 → 전처리 → 분석 → 리포트 생성 → 이메일 발송 → DB 저장
"""

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (Lambda 및 로컬 실행 호환)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import LOG_LEVEL
from collector.naver_collector import NaverCollector
from processor.text_processor import TextProcessor
from analyzer.claude_analyzer import ClaudeAnalyzer
from report.generator import ReportGenerator
from mailer.sendgrid_mailer import SendGridMailer
from db.supabase_client import SupabaseClient

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_week_range() -> tuple[str, str]:
    """지난 7일간의 날짜 범위를 계산한다."""
    now = datetime.now(timezone.utc)
    week_end = now.strftime("%Y-%m-%d")
    week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    return week_start, week_end


def handler(event=None, context=None) -> dict:
    """주간 리포트 생성 및 발송 파이프라인."""
    logger.info("=" * 60)
    logger.info("주간 리포트 파이프라인 시작")
    logger.info("=" * 60)

    week_start, week_end = get_week_range()
    week_label = f"{week_start}~{week_end}"
    logger.info(f"대상 기간: {week_label}")

    result = {
        "week": week_label,
        "status": "started",
        "steps": {},
    }

    try:
        # 1. 데이터 수집
        logger.info("[1/6] 네이버 카페 게시글 수집 시작")
        collector = NaverCollector()
        raw_posts = collector.collect_weekly_posts(days_back=7)
        result["steps"]["collect"] = {"raw_count": len(raw_posts)}

        if len(raw_posts) < 10:
            logger.warning(f"수집된 게시글이 {len(raw_posts)}건으로 적습니다. 계속 진행합니다.")

        if len(raw_posts) == 0:
            logger.error("수집된 게시글이 없습니다. 파이프라인을 중단합니다.")
            result["status"] = "failed"
            result["error"] = "수집된 게시글 없음"
            return result

        # 2. 텍스트 전처리
        logger.info("[2/6] 텍스트 전처리 시작")
        processor = TextProcessor()
        cleaned_posts = processor.clean_posts(raw_posts)
        aggregated_text = processor.aggregate_for_analysis(cleaned_posts)
        result["steps"]["process"] = {"cleaned_count": len(cleaned_posts)}

        # 3. AI 분석
        logger.info("[3/6] Claude AI 분석 시작")
        analyzer = ClaudeAnalyzer()
        analysis = analyzer.analyze(
            aggregated_text=aggregated_text,
            week_start=week_start,
            week_end=week_end,
            post_count=len(cleaned_posts),
        )

        if "error" in analysis:
            logger.error(f"AI 분석 실패: {analysis['error']}")
            result["status"] = "failed"
            result["error"] = analysis["error"]
            return result

        result["steps"]["analyze"] = {"status": "success"}

        # 4. 구독자 조회
        logger.info("[4/6] 구독자 조회")
        db = SupabaseClient()
        subscribers = db.get_active_subscribers()

        if not subscribers:
            logger.warning("활성 구독자가 없습니다.")
            result["steps"]["subscribers"] = {"count": 0}
            result["status"] = "completed_no_subscribers"
            return result

        result["steps"]["subscribers"] = {"count": len(subscribers)}

        # 5. 리포트 생성 및 이메일 발송
        logger.info(f"[5/6] {len(subscribers)}명에게 리포트 발송 시작")
        report_gen = ReportGenerator()
        mailer = SendGridMailer()

        def generate_personalized_html(subscriber: dict) -> str:
            return report_gen.generate_html(analysis, subscriber, week_start, week_end)

        send_result = mailer.send_batch(
            subscribers=subscribers,
            html_generator_fn=generate_personalized_html,
            week_label=week_label,
        )
        result["steps"]["send"] = send_result

        # 6. DB에 리포트 저장
        logger.info("[6/6] 리포트 DB 저장")
        report_id = db.save_report({
            "week_start": week_start,
            "week_end": week_end,
            "raw_posts": json.loads(json.dumps(raw_posts, ensure_ascii=False, default=str)),
            "analysis": analysis,
            "html_content": generate_personalized_html(subscribers[0]),
            "recipient_count": send_result["success"],
        })
        db.update_report_sent(report_id, send_result["success"])

        # 발송 로그 저장
        for detail in send_result.get("details", []):
            db.log_send(
                report_id=report_id,
                subscriber_id=detail["subscriber_id"],
                status=detail["status"],
            )

        result["steps"]["save"] = {"report_id": report_id}
        result["status"] = "completed"

        logger.info("=" * 60)
        logger.info(f"파이프라인 완료: 성공 {send_result['success']}건, 실패 {send_result['failed']}건")
        logger.info("=" * 60)

    except Exception as e:
        logger.exception(f"파이프라인 오류 발생: {e}")
        result["status"] = "error"
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    result = handler()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
