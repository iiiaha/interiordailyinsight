"""게시글 목록 페이지의 frame 구조를 디버깅한다."""

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
    print(f"로그인 후: {page.url}")

    # 전체글보기로 직접 이동 (iframe URL 직접 접근)
    # 방법 1: iframe URL에 직접 접근
    direct_url = f"https://cafe.naver.com/ArticleList.nhn?search.clubid={CLUB_ID}&search.boardtype=L&search.page=1"
    print(f"\n=== 방법 1: iframe URL 직접 접근 ===")
    page.goto(direct_url)
    time.sleep(3)
    print(f"현재 URL: {page.url}")
    print(f"프레임 수: {len(page.frames)}")

    for i, frame in enumerate(page.frames):
        print(f"  Frame {i}: {frame.url[:120]}")

    # board-box 찾기
    for i, frame in enumerate(page.frames):
        rows = frame.query_selector_all("table.board-box tbody tr")
        if rows:
            print(f"\n  Frame {i}에서 table.board-box tr 발견: {len(rows)}개")
            for j, row in enumerate(rows[:3]):
                link = row.query_selector("a.article")
                date = row.query_selector("td.td_date")
                if link:
                    print(f"    [{j}] 제목: {(link.get_attribute('title') or link.inner_text())[:60]}")
                    print(f"         href: {link.get_attribute('href')[:100]}")
                if date:
                    print(f"         날짜: {date.inner_text()}")

    # 방법 2: 카페 메인 + iframe_url
    print(f"\n=== 방법 2: cafe.naver.com/overseer?iframe_url= ===")
    iframe_url = f"https://cafe.naver.com/overseer?iframe_url=/ArticleList.nhn%3Fsearch.clubid={CLUB_ID}%26search.boardtype=L%26search.page=1"
    page.goto(iframe_url)
    time.sleep(3)
    print(f"현재 URL: {page.url}")
    print(f"프레임 수: {len(page.frames)}")

    for i, frame in enumerate(page.frames):
        print(f"  Frame {i}: {frame.url[:120]}")
        rows = frame.query_selector_all("table.board-box tbody tr")
        if rows:
            print(f"    -> board-box tr 발견: {len(rows)}개")
            for j, row in enumerate(rows[:3]):
                link = row.query_selector("a.article")
                date = row.query_selector("td.td_date")
                if link:
                    print(f"    [{j}] 제목: {(link.get_attribute('title') or link.inner_text())[:60]}")
                if date:
                    print(f"         날짜: {date.inner_text()}")

    # 방법 3: 카페 메인 갔다가 전체글보기 클릭
    print(f"\n=== 방법 3: 카페 메인에서 전체글보기 링크 찾기 ===")
    page.goto("https://cafe.naver.com/overseer")
    time.sleep(3)

    for i, frame in enumerate(page.frames):
        links = frame.query_selector_all("a")
        for link in links:
            text = (link.inner_text() or "").strip()
            href = link.get_attribute("href") or ""
            if "전체글" in text or "boardtype=L" in href:
                print(f"  Frame {i}: '{text}' -> {href[:100]}")

    browser.close()
    print("\n완료")
