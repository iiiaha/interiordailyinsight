"""게시판 분류(카테고리) 정보 구조 확인."""
import os, sys, time
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

    # login
    page.goto("https://nid.naver.com/nidlogin.login")
    time.sleep(2)
    page.evaluate(f"document.querySelector('#id').value = '{naver_id}'; document.querySelector('#pw').value = '{naver_pw}';")
    time.sleep(1)
    page.click("#log\\.login")
    time.sleep(5)

    # page 1
    page.goto(f"https://cafe.naver.com/f-e/cafes/{CLUB_ID}/menus/0?viewType=L&page=1")
    time.sleep(4)

    # 전체 row context 확인 - a[href*=articles] 주변 텍스트
    links = page.query_selector_all("a[href*='/articles/']")
    seen = set()
    for link in links:
        href = link.get_attribute("href") or ""
        if "commentFocus" in href or "referrerAllArticles=false" in href:
            continue
        if href in seen:
            continue
        seen.add(href)

        # 행 전체 텍스트
        row_text = link.evaluate("""el => {
            let row = el.closest('tr') || el.closest('li') || el.parentElement?.parentElement?.parentElement;
            if (!row) return '';
            // 각 td/셀 텍스트를 | 로 구분
            let cells = row.querySelectorAll('td, [class*=cell], [class*=col]');
            if (cells.length > 0) {
                return Array.from(cells).map(c => c.innerText.trim()).join(' | ');
            }
            return row.innerText;
        }""") or ""

        # 게시판 분류만 추출 시도
        board_name = link.evaluate("""el => {
            let row = el.closest('tr') || el.closest('li') || el.parentElement?.parentElement?.parentElement;
            if (!row) return '';
            // 첫 번째 td가 게시판 분류일 수 있음
            let firstTd = row.querySelector('td:first-child, [class*=board], [class*=cate], [class*=menu]');
            return firstTd ? firstTd.innerText.trim() : '';
        }""") or ""

        print(f"board: [{board_name[:30]}] | row: {row_text[:150]}")

    browser.close()
    print("\ncomplete")
