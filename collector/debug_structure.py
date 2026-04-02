"""카페 HTML 구조를 디버깅하기 위한 스크립트."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from playwright.sync_api import sync_playwright

NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
CAFE_URL = "https://cafe.naver.com/overseer"

naver_id = os.getenv("NAVER_ID")
naver_pw = os.getenv("NAVER_PW")

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
    page.goto(NAVER_LOGIN_URL)
    time.sleep(2)
    page.evaluate(f"""
        document.querySelector('#id').value = '{naver_id}';
        document.querySelector('#pw').value = '{naver_pw}';
    """)
    time.sleep(1)
    page.click("#log\\.login")
    time.sleep(5)

    print(f"로그인 후 URL: {page.url}")

    # 카페 메인으로 이동
    page.goto(CAFE_URL)
    time.sleep(3)
    print(f"카페 URL: {page.url}")

    # 모든 frame 정보 출력
    print(f"\n=== 프레임 목록 ({len(page.frames)}개) ===")
    for i, frame in enumerate(page.frames):
        print(f"  Frame {i}: {frame.url[:100]}")

    # 각 frame에서 게시글 관련 요소 탐색
    for i, frame in enumerate(page.frames):
        print(f"\n=== Frame {i} 분석 ===")
        print(f"  URL: {frame.url[:120]}")

        # 다양한 selector 시도
        selectors = [
            "a.article",
            ".article-board",
            ".board-list",
            "#main-area",
            ".article_lst",
            ".list-tit",
            "table.board-box",
            ".inner_list",
            ".article_title",
            ".board_box",
            ".article-board-list",
            "ul.article-movie-sub",
            ".ArticleListItem",
            "[class*=article]",
            "[class*=Article]",
            "[class*=board]",
            "[class*=Board]",
            "[class*=list]",
        ]

        for sel in selectors:
            try:
                els = frame.query_selector_all(sel)
                if els:
                    print(f"  FOUND: '{sel}' → {len(els)}개")
                    # 첫 번째 요소의 텍스트와 HTML 미리보기
                    if len(els) > 0:
                        text = (els[0].inner_text() or "")[:100]
                        html = (els[0].evaluate("el => el.outerHTML") or "")[:200]
                        print(f"    텍스트: {text}")
                        print(f"    HTML: {html}")
            except:
                pass

    # 페이지 전체 HTML 저장
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    page.screenshot(path=str(data_dir / "cafe_screenshot.png"), full_page=True)
    print(f"\n스크린샷 저장: data/cafe_screenshot.png")

    # 각 frame HTML 저장
    for i, frame in enumerate(page.frames):
        try:
            html = frame.content()
            with open(data_dir / f"frame_{i}.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Frame {i} HTML 저장: data/frame_{i}.html ({len(html)}자)")
        except:
            pass

    browser.close()
    print("\n완료")
