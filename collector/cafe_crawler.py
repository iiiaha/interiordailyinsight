"""네이버 카페 'overseer(셀프인테리어)' Playwright 기반 크롤러.

네이버 카페 새 UI(f-e) 기반으로 로그인 후 전체글보기에서
최근 7일간 게시글의 제목 + 게시판 분류 + 링크를 수집한다.
본문은 수집하지 않고, 제목만으로 AI 분석을 수행한다.
"""

import json
import logging
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

logger = logging.getLogger(__name__)

CAFE_ID = "overseer"
CLUB_ID = "23700418"
CAFE_BASE = f"https://cafe.naver.com/f-e/cafes/{CLUB_ID}"
NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# 필터링할 게시판 분류 (업체 홍보성)
EXCLUDE_BOARDS = [
    "(업체가 쓴)",
    "(광고)",
]


class CafeCrawler:
    """네이버 카페 게시글 제목을 Playwright로 크롤링한다."""

    def __init__(self, naver_id: str, naver_pw: str, headless: bool = False):
        self.naver_id = naver_id
        self.naver_pw = naver_pw
        self.headless = headless
        self.posts: list[dict] = []

    def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        time.sleep(random.uniform(min_sec, max_sec))

    def _login(self, page: Page) -> bool:
        """네이버 로그인."""
        logger.info("네이버 로그인 시도...")
        try:
            page.goto(NAVER_LOGIN_URL, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            logger.error(f"로그인 페이지 로드 실패: {e}")
            return False
        self._random_delay(2, 3)

        # ID/PW 입력 (JS 주입)
        try:
            page.evaluate(f"""
                document.querySelector('#id').value = '{self.naver_id}';
                document.querySelector('#pw').value = '{self.naver_pw}';
            """)
        except Exception as e:
            logger.error(f"ID/PW 입력 실패: {e}")
            return False
        self._random_delay(0.5, 1)

        # 로그인 버튼 클릭
        try:
            page.click("#log\\.login", timeout=5000)
        except Exception:
            # 버튼 셀렉터가 다를 수 있음
            try:
                page.click("button[type='submit']", timeout=5000)
            except Exception as e:
                logger.error(f"로그인 버튼 클릭 실패: {e}")
                return False
        self._random_delay(3, 5)

        # 로그인 성공 확인
        if "nid.naver.com" in page.url:
            logger.warning("추가 인증 필요. 브라우저에서 수동 처리하세요.")
            if not self.headless:
                try:
                    page.wait_for_url("https://www.naver.com/**", timeout=60000)
                except:
                    pass

        if "naver.com" in page.url and "nidlogin" not in page.url:
            logger.info("네이버 로그인 성공")
            return True

        logger.error(f"로그인 실패: {page.url}")
        return False

    def _parse_date(self, date_str: str) -> datetime | None:
        """날짜 파싱. '21:37' -> 오늘, '2026.04.01.' -> 해당 날짜."""
        if not date_str:
            return None
        date_str = date_str.strip()
        now = datetime.now()

        if re.match(r"^\d{1,2}:\d{2}$", date_str):
            return now.replace(hour=0, minute=0, second=0, microsecond=0)

        for fmt in ["%Y.%m.%d.", "%Y.%m.%d", "%Y-%m-%d"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def _extract_article_id(self, href: str) -> str:
        match = re.search(r"/articles/(\d+)", href)
        return match.group(1) if match else ""

    def _is_excluded_board(self, board_name: str) -> bool:
        """업체 홍보 등 제외 대상 게시판인지 확인."""
        for pattern in EXCLUDE_BOARDS:
            if pattern in board_name:
                return True
        return False

    def _get_article_list(self, page: Page, max_pages: int = 100, days_back: int = 7) -> list[dict]:
        """전체글보기에서 게시글 제목 목록을 수집한다."""
        articles = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        seen_ids: set[str] = set()
        excluded_count = 0

        for page_num in range(1, max_pages + 1):
            logger.info(f"목록 {page_num}페이지 수집 중... (누적 {len(articles)}건)")

            url = f"{CAFE_BASE}/menus/0?viewType=L&page={page_num}"
            page.goto(url)
            self._random_delay(1.5, 3.0)

            links = page.query_selector_all("a[href*='/articles/']")

            found_old = False
            page_count = 0

            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    if "/articles/" not in href:
                        continue
                    if "commentFocus=true" in href:
                        continue
                    if "referrerAllArticles=false" in href:
                        continue

                    article_id = self._extract_article_id(href)
                    if not article_id or article_id in seen_ids:
                        continue
                    seen_ids.add(article_id)

                    title = (link.get_attribute("title") or link.inner_text() or "").strip()
                    if not title:
                        continue

                    # 행에서 게시판 분류 + 날짜 추출
                    row_info = link.evaluate("""el => {
                        let row = el.closest('tr') || el.closest('li') || el.parentElement?.parentElement?.parentElement;
                        if (!row) return {board: '', date: ''};
                        let firstTd = row.querySelector('td:first-child');
                        let board = firstTd ? firstTd.innerText.trim() : '';
                        let text = row.innerText || '';
                        return {board: board, text: text};
                    }""") or {}

                    board_name = row_info.get("board", "")
                    row_text = row_info.get("text", "")

                    # 업체 홍보 게시판 필터링
                    if self._is_excluded_board(board_name):
                        excluded_count += 1
                        continue

                    # 날짜 추출
                    date_str = ""
                    date_match = re.search(r"(\d{4}\.\d{2}\.\d{2}\.?)", row_text)
                    if date_match:
                        date_str = date_match.group(1)
                    else:
                        time_match = re.search(r"\t(\d{1,2}:\d{2})\t", row_text)
                        if time_match:
                            date_str = time_match.group(1)

                    article_date = self._parse_date(date_str)

                    # 7일 이전 게시글이면 종료
                    if article_date and article_date < cutoff_date:
                        found_old = True
                        break

                    articles.append({
                        "article_id": article_id,
                        "title": title,
                        "board": board_name,
                        "date_str": date_str,
                        "date": article_date.isoformat() if article_date else None,
                        "url": f"{CAFE_BASE}/articles/{article_id}",
                    })
                    page_count += 1

                except Exception as e:
                    logger.debug(f"파싱 오류: {e}")
                    continue

            logger.info(f"  {page_num}p: +{page_count}건 (업체글 제외: {excluded_count}건)")

            if found_old:
                logger.info(f"  {days_back}일 이전 게시글 도달 - 수집 종료")
                break

            if page_count == 0 and page_num > 3:
                logger.info(f"  새 게시글 없음 - 수집 종료")
                break

        logger.info(f"목록 수집 완료: {len(articles)}건 (업체글 {excluded_count}건 제외)")
        return articles

    def crawl(self, days_back: int = 7, max_pages: int = 100) -> list[dict]:
        """제목 기반 크롤링 파이프라인."""
        logger.info("=" * 50)
        logger.info(f"카페 크롤링 시작: {CAFE_ID} (최근 {days_back}일, 제목만)")
        logger.info("=" * 50)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                locale="ko-KR",
            )
            page = context.new_page()

            if not self._login(page):
                browser.close()
                return []

            self._random_delay(1, 2)
            articles = self._get_article_list(page, max_pages=max_pages, days_back=days_back)
            browser.close()

        if not articles:
            logger.warning("수집된 게시글이 없습니다.")
            return []

        # 게시판별 통계
        board_stats: dict[str, int] = {}
        for a in articles:
            b = a.get("board", "기타")
            board_stats[b] = board_stats.get(b, 0) + 1

        logger.info("게시판별 수집 현황:")
        for board, count in sorted(board_stats.items(), key=lambda x: -x[1]):
            logger.info(f"  {board}: {count}건")

        self._save_raw(articles)
        self.posts = articles
        return articles

    def _save_raw(self, posts: list[dict]):
        DATA_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = DATA_DIR / f"crawl_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"수집 데이터 저장: {filepath}")


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    naver_id = os.getenv("NAVER_ID", "")
    naver_pw = os.getenv("NAVER_PW", "")

    if not naver_id or not naver_pw:
        print("NAVER_ID와 NAVER_PW를 .env에 설정하세요.")
        sys.exit(1)

    crawler = CafeCrawler(naver_id=naver_id, naver_pw=naver_pw, headless=False)
    posts = crawler.crawl(days_back=1, max_pages=100)

    print(f"\n=== 수집 완료: {len(posts)}건 ===")
    for p in posts[:10]:
        print(f"  [{p.get('board', '')[:15]}] {p['title'][:50]} ({p['date_str']})")
