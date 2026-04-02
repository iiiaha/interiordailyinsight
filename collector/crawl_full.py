"""오늘 수집된 제목 목록을 기반으로 본문 + 댓글을 수집한다."""

import json
import logging
import os
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

naver_id = os.getenv("NAVER_ID")
naver_pw = os.getenv("NAVER_PW")

# 기존 제목 데이터 로드
title_file = DATA_DIR / "crawl_20260401_215858.json"
with open(title_file, "r", encoding="utf-8") as f:
    articles = json.load(f)

logger.info(f"본문+댓글 수집 대상: {len(articles)}건")

# 본문 selectors
CONTENT_SELECTORS = [
    ".se-main-container",
    ".ContentRenderer",
    "#postContent",
    ".article_viewer",
    "#tbody",
    ".NHN_Writeform_Main",
    "article",
    "[class*='ArticleContentBox']",
]

# 댓글 selectors
COMMENT_SELECTORS = [
    ".comment_list",
    ".CommentBox",
    "#cmt_list",
    "[class*='comment_area']",
    "[class*='CommentList']",
    ".u_cbox_list",
]


def get_content_and_comments(page, article_url: str) -> tuple[str | None, list[str]]:
    """게시글 본문과 댓글을 가져온다."""
    content = None
    comments = []

    try:
        page.goto(article_url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(random.uniform(1.5, 2.5))

        # 모든 대상 (메인 + frames)
        targets = [page] + [f for f in page.frames if f != page.main_frame]

        # 본문 수집
        for target in targets:
            if content:
                break
            for sel in CONTENT_SELECTORS:
                try:
                    el = target.query_selector(sel)
                    if el:
                        text = (el.inner_text() or "").strip()
                        if len(text) > 20:
                            content = text
                            break
                except:
                    continue

        # 댓글 수집 — 개별 댓글 텍스트 추출
        for target in targets:
            # 방법 1: 댓글 컨테이너에서 개별 댓글 추출
            try:
                comment_items = target.query_selector_all(
                    ".comment_text_box, .u_cbox_text_wrap, "
                    "[class*='comment_text'], [class*='CommentItem'], "
                    ".txt_comment, .comment_inbox .text_comment"
                )
                if comment_items:
                    for item in comment_items:
                        text = (item.inner_text() or "").strip()
                        if text and len(text) > 2:
                            comments.append(text)
                    break
            except:
                continue

            # 방법 2: 댓글 영역 전체 텍스트
            if not comments:
                for sel in COMMENT_SELECTORS:
                    try:
                        el = target.query_selector(sel)
                        if el:
                            raw = (el.inner_text() or "").strip()
                            if raw and len(raw) > 5:
                                # 줄 단위로 분리해서 의미있는 것만
                                for line in raw.split("\n"):
                                    line = line.strip()
                                    if len(line) > 5 and not line.startswith("답글") and not line.isdigit():
                                        comments.append(line)
                                break
                    except:
                        continue

        return content, comments

    except Exception as e:
        logger.warning(f"수집 실패: {e}")
        return None, []


with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        locale="ko-KR",
    )
    page = context.new_page()

    # 로그인
    logger.info("네이버 로그인...")
    page.goto(NAVER_LOGIN_URL)
    time.sleep(2)
    page.evaluate(f"""
        document.querySelector('#id').value = '{naver_id}';
        document.querySelector('#pw').value = '{naver_pw}';
    """)
    time.sleep(1)
    try:
        page.click("#log\\.login", timeout=5000)
    except:
        page.click("button[type='submit']", timeout=5000)
    time.sleep(5)

    if "nid.naver.com" in page.url:
        logger.warning("추가 인증 필요 — 브라우저에서 처리하세요")
        try:
            page.wait_for_url("https://www.naver.com/**", timeout=60000)
        except:
            pass

    logger.info(f"로그인 완료: {page.url}")

    # 본문 + 댓글 수집
    content_ok = 0
    comment_ok = 0
    fail = 0
    total = len(articles)
    start_time = time.time()

    for i, article in enumerate(articles):
        title_short = article["title"][:30]

        content, comments = get_content_and_comments(page, article["url"])

        if content:
            article["content"] = content
            content_ok += 1
        else:
            article["content"] = ""
            fail += 1

        article["comments"] = comments
        if comments:
            comment_ok += 1

        # 10건마다 로그
        if (i + 1) % 10 == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            remaining = (total - i - 1) / rate if rate > 0 else 0
            logger.info(
                f"  [{i+1}/{total}] 본문:{content_ok} 댓글:{comment_ok} 실패:{fail} "
                f"| 남은시간: {remaining/60:.0f}분"
            )

        # 50건마다 중간 저장
        if (i + 1) % 50 == 0:
            temp_file = DATA_DIR / "crawl_full_temp.json"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(articles, f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"  === 중간 저장 완료 ({i+1}/{total}) ===")

    browser.close()

# 최종 저장
output_file = DATA_DIR / "crawl_full_20260401.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(articles, f, ensure_ascii=False, indent=2, default=str)

elapsed_total = time.time() - start_time
logger.info(f"=" * 50)
logger.info(f"수집 완료! 총 {elapsed_total/60:.1f}분 소요")
logger.info(f"  본문 성공: {content_ok}/{total}건")
logger.info(f"  댓글 있는 글: {comment_ok}/{total}건")
logger.info(f"  실패: {fail}건")
logger.info(f"저장: {output_file}")
