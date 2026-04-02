"""방법 2의 Frame 6에서 실제 데이터 추출 테스트."""

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

    # 방법 2: iframe_url
    url = f"https://cafe.naver.com/overseer?iframe_url=/ArticleList.nhn%3Fsearch.clubid={CLUB_ID}%26search.boardtype=L%26search.page=1"
    page.goto(url)
    time.sleep(4)

    # Frame 6 직접 접근
    target_frame = None
    for frame in page.frames:
        if "ArticleList.nhn" in frame.url:
            target_frame = frame
            print(f"타겟 프레임 발견: {frame.url[:100]}")
            break

    if target_frame:
        # board-box 시도
        rows = target_frame.query_selector_all("table.board-box tbody tr")
        print(f"table.board-box tbody tr: {len(rows)}개")

        if not rows:
            rows = target_frame.query_selector_all("table.board-box tr")
            print(f"table.board-box tr: {len(rows)}개")

        if not rows:
            # 모든 a.article 직접 찾기
            articles = target_frame.query_selector_all("a.article")
            print(f"a.article: {len(articles)}개")
            for i, a in enumerate(articles[:10]):
                title = a.get_attribute("title") or a.inner_text()
                href = a.get_attribute("href") or ""
                print(f"  [{i}] {title[:60]} | {href[:80]}")

            # td.td_date 직접 찾기
            dates = target_frame.query_selector_all("td.td_date")
            print(f"\ntd.td_date: {len(dates)}개")
            for i, d in enumerate(dates[:10]):
                print(f"  [{i}] {d.inner_text()}")
        else:
            for i, row in enumerate(rows[:15]):
                link = row.query_selector("a.article")
                date = row.query_selector("td.td_date")
                if link:
                    title = link.get_attribute("title") or link.inner_text()
                    print(f"  [{i}] {title[:60]} | 날짜: {date.inner_text() if date else 'N/A'}")
    else:
        print("타겟 프레임을 찾지 못함")

    # 새 UI 방법도 테스트
    print(f"\n=== 새 UI 테스트 ===")
    new_url = f"https://cafe.naver.com/f-e/cafes/{CLUB_ID}/menus/0?viewType=L&page=1"
    page.goto(new_url)
    time.sleep(4)
    print(f"URL: {page.url}")

    # 새 UI의 게시글 요소 탐색
    for sel in ["a[href*='articles']", "[class*=Article]", "[class*=article]", "[class*=item]", "[class*=Item]", "[class*=post]", "[class*=Post]"]:
        els = page.query_selector_all(sel)
        if els:
            print(f"  '{sel}': {len(els)}개")
            for e in els[:3]:
                text = (e.inner_text() or "")[:80].replace("\n", " ")
                href = e.get_attribute("href") or ""
                print(f"    text: {text}")
                if href:
                    print(f"    href: {href[:100]}")

    browser.close()
    print("\n완료")
