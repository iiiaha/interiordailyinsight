"""네이버 검색 API를 통한 카페 게시글 수집 모듈."""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

from config.settings import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, SEARCH_KEYWORDS

logger = logging.getLogger(__name__)

# 네이버 카페 게시글 검색 API 엔드포인트
NAVER_CAFE_API = "https://openapi.naver.com/v1/search/cafearticle.json"


class NaverCollector:
    """네이버 검색 API를 사용하여 인테리어 관련 카페 게시글을 수집한다."""

    def __init__(self):
        self.headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _search_keyword(self, keyword: str, display: int = 100, start: int = 1) -> list[dict]:
        """단일 키워드로 네이버 카페 게시글을 검색한다."""
        params = {
            "query": keyword,
            "display": display,
            "start": start,
            "sort": "date",
        }
        try:
            response = self.session.get(NAVER_CAFE_API, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            logger.info(f"[{keyword}] {len(items)}건 검색 완료 (총 {data.get('total', 0)}건)")
            return items
        except requests.RequestException as e:
            logger.error(f"[{keyword}] 검색 실패: {e}")
            return []

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """네이버 API의 날짜 문자열을 파싱한다."""
        # 네이버 API pubDate 형식: "Mon, 01 Apr 2026 09:00:00 +0900"
        try:
            return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        except (ValueError, TypeError):
            return None

    def _is_within_days(self, date_str: str, days_back: int) -> bool:
        """게시글이 지정 일수 이내인지 확인한다."""
        parsed = self._parse_date(date_str)
        if not parsed:
            return False
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        return parsed >= cutoff

    def collect_weekly_posts(
        self,
        keywords: Optional[list[str]] = None,
        days_back: int = 7,
    ) -> list[dict]:
        """지난 N일간의 카페 게시글을 수집한다."""
        keywords = keywords or SEARCH_KEYWORDS
        all_posts: list[dict] = []
        seen_links: set[str] = set()
        stats: dict[str, int] = {}

        for keyword in keywords:
            keyword_count = 0

            # 최대 3페이지까지 수집 (100 * 3 = 300건)
            for start in range(1, 301, 100):
                items = self._search_keyword(keyword, display=100, start=start)
                if not items:
                    break

                for item in items:
                    link = item.get("link", "")

                    # 중복 제거
                    if link in seen_links:
                        continue

                    # 날짜 필터
                    if not self._is_within_days(item.get("pubDate", ""), days_back):
                        continue

                    seen_links.add(link)
                    all_posts.append({
                        "title": item.get("title", ""),
                        "description": item.get("description", ""),
                        "link": link,
                        "pub_date": item.get("pubDate", ""),
                        "cafe_name": item.get("cafename", ""),
                        "keyword": keyword,
                    })
                    keyword_count += 1

                # 다음 페이지 요청 전 대기 (rate limiting)
                time.sleep(0.5)

            stats[keyword] = keyword_count
            logger.info(f"[{keyword}] 최종 수집: {keyword_count}건")

            # 키워드 간 대기
            time.sleep(0.3)

        # 수집 통계 로깅
        total = len(all_posts)
        logger.info(f"전체 수집 완료: {total}건")
        for kw, count in stats.items():
            logger.info(f"  - {kw}: {count}건")

        return all_posts
