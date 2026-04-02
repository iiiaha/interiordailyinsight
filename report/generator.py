"""주간 리포트 HTML 생성 모듈."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from config.settings import SERVICE_DOMAIN, PROJECT_ROOT

logger = logging.getLogger(__name__)

TEMPLATE_DIR = PROJECT_ROOT / "report" / "templates"


class ReportGenerator:
    """분석 결과를 기반으로 HTML 리포트를 생성한다."""

    def __init__(self):
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=True,
        )
        self.template = self.env.get_template("weekly_report.html")

    def generate_html(
        self,
        analysis: dict,
        subscriber: dict,
        week_start: str,
        week_end: str,
    ) -> str:
        """분석 결과와 구독자 정보로 개인화된 HTML 리포트를 생성한다."""
        unsubscribe_url = f"{SERVICE_DOMAIN}/unsubscribe?token={subscriber.get('id', '')}"

        html = self.template.render(
            analysis=analysis,
            week_start=week_start,
            week_end=week_end,
            subscriber_name=subscriber.get("name"),
            unsubscribe_url=unsubscribe_url,
        )

        logger.info(f"HTML 리포트 생성 완료: {len(html)}자")
        return html
