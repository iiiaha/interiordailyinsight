"""새 UI에서 게시글 목록 + 개별 본문 구조 파악."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from playwright.sync_api import sync_playwright

naver_id = os.getenv("NAVER_ID")
naver_pw = os.getenv("NAVER_PW")
CLUB_ID = "23700418"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        locale="ko-KR",
    )
    page = context.new_page()

    # 로그인
    page.goto("https://nid.naver.com/nidlogin.login")
    time.sleep(2)
    page.evaluate(f"document.querySelector('#id').value = '{naver_id}'; document.querySelector('#pw').value = '{naver_pw}';")
    time.sleep(1)
    page.click("#log\\.login")
    time.sleep(5)

    # 새 UI 전체글보기
    page.goto(f"https://cafe.naver.com/f-e/cafes/{CLUB_ID}/menus/0?viewType=L&page=1")
    time.sleep(4)

    # 게시글 링크 추출
    links = page.query_selector_all("a[href*='articles']")
    print(f"게시글 링크 수: {len(links)}")

    articles = []
    seen = set()
    for link in links:
        href = link.get_attribute("href") or ""
        text = (link.inner_text() or "").strip()

        # articles/숫자 패턴만 추출
        if "/articles/" not in href:
            continue

        # 중복 제거
        if href in seen:
            continue
        seen.add(href)

        # 부모 요소에서 날짜 찾기
        parent = link.evaluate("el => { let p = el.closest('tr') || el.closest('li') || el.closest('[class*=item]') || el.parentElement?.parentElement?.parentElement; return p ? p.innerText : ''; }")

        articles.append({"text": text[:60], "href": href[:120], "context": (parent or "")[:200].replace("\n", " | ")})

    print(f"\n유니크 게시글: {len(articles)}개\n")
    for i, a in enumerate(articles[:15]):
        print(f"[{i}] {a['text']}")
        print(f"     href: {a['href']}")
        print(f"     context: {a['context'][:120]}")
        print()

    # 첫 번째 일반 게시글 (공지 아닌것) 본문 테스트
    if len(articles) > 6:
        test_article = articles[6]  # 공지 다음 첫 번째 글
        print(f"\n=== 본문 테스트: {test_article['text']} ===")
        page.goto(test_article["href"])
        time.sleep(4)

        print(f"URL: {page.url}")
        print(f"프레임: {len(page.frames)}")

        # 본문 selector 탐색
        for sel in [".se-main-container", ".ContentRenderer", "#postContent", ".article_viewer",
                    "article", "[class*=content]", "[class*=Content]", "[class*=viewer]", "[class*=body]",
                    ".ArticleContentBox", ".article_container"]:
            # 페이지에서
            el = page.query_selector(sel)
            if el:
                text = (el.inner_text() or "")[:200]
                print(f"  PAGE '{sel}': {text[:100]}...")

            # 각 frame에서
            for fi, frame in enumerate(page.frames):
                if frame == page.main_frame:
                    continue
                el = frame.query_selector(sel)
                if el:
                    text = (el.inner_text() or "")[:200]
                    print(f"  FRAME{fi} '{sel}': {text[:100]}...")

    browser.close()
    print("\n완료")
