"""네이버 로그인 후 쿠키를 파일로 저장한다.

최초 1회 실행하여 쿠키를 저장하면,
이후 크롤러는 이 쿠키로 로그인 없이 카페에 접근할 수 있다.
쿠키 만료 시 다시 실행하면 된다.
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from playwright.sync_api import sync_playwright

NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
COOKIE_FILE = Path(__file__).resolve().parent.parent / "data" / "naver_cookies.json"

naver_id = os.getenv("NAVER_ID")
naver_pw = os.getenv("NAVER_PW")

print("=" * 50)
print("네이버 쿠키 저장 스크립트")
print("브라우저가 열리면 로그인을 완료하세요.")
print("2차 인증이 뜨면 직접 처리하세요.")
print("=" * 50)

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

    # 로그인 페이지 이동
    page.goto(NAVER_LOGIN_URL)
    time.sleep(2)

    # ID/PW 입력
    page.evaluate(f"""
        document.querySelector('#id').value = '{naver_id}';
        document.querySelector('#pw').value = '{naver_pw}';
    """)
    time.sleep(1)

    # 로그인 버튼 클릭
    try:
        page.click("#log\\.login", timeout=5000)
    except:
        page.click("button[type='submit']", timeout=5000)

    # 로그인 완료 대기 (2차 인증 포함 최대 60초)
    print("\n로그인 처리 중... (2차 인증 뜨면 직접 처리하세요)")
    for i in range(60):
        time.sleep(1)
        if "naver.com" in page.url and "nidlogin" not in page.url:
            break

    if "nidlogin" in page.url:
        print("로그인 추가 인증 필요. 브라우저에서 처리하세요. 60초 대기...")
        try:
            page.wait_for_url("https://www.naver.com/**", timeout=60000)
        except:
            pass

    # 카페 접속 확인
    page.goto("https://cafe.naver.com/overseer")
    time.sleep(3)
    print(f"현재 URL: {page.url}")

    # 쿠키 저장
    cookies = context.cookies()
    COOKIE_FILE.parent.mkdir(exist_ok=True)
    with open(COOKIE_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)

    print(f"\n쿠키 저장 완료: {COOKIE_FILE}")
    print(f"쿠키 수: {len(cookies)}개")

    browser.close()

print("\n이제 크롤러가 이 쿠키를 사용하여 로그인 없이 동작합니다.")
