import sys,json
sys.path.insert(0,'/opt/idi')
from dotenv import load_dotenv
load_dotenv('/opt/idi/.env')

# 댓글 0개였던 글 5개로 테스트
data=json.load(open('/opt/idi/data/crawl_2026-04-04.json'))
no_comments=[d for d in data if len(d.get('comments',[]))==0 and d.get('content')][:5]
print(f"Testing {len(no_comments)} posts that had 0 comments before")

from playwright.sync_api import sync_playwright
import time,random

COOKIE_FILE='/opt/idi/data/naver_cookies.json'
CONTENT_SELECTORS = [
    ".se-main-container", ".ContentRenderer", "#postContent",
    ".article_viewer", "#tbody", ".NHN_Writeform_Main",
    "article", "[class*='ArticleContentBox']",
]

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    context=browser.new_context(
        viewport={"width":1280,"height":900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        locale="ko-KR",
    )
    cookies=json.load(open(COOKIE_FILE))
    context.add_cookies(cookies)
    page=context.new_page()

    for article in no_comments:
        title=article['title'][:30]
        print(f"\n--- {title} ---")

        page.goto(article["url"], wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)

        targets = [page] + [f for f in page.frames if f != page.main_frame]

        # 새 로직: 모든 frame 스크롤
        for target in targets:
            try:
                target.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except:
                pass
        time.sleep(2)
        for target in targets:
            try:
                target.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except:
                pass
        time.sleep(2)

        # 댓글 수집
        comments = []
        for target in targets:
            try:
                items = target.query_selector_all(
                    ".comment_text_box, .u_cbox_text_wrap, "
                    "[class*='comment_text'], [class*='CommentItem'], "
                    ".txt_comment, .comment_inbox .text_comment"
                )
                if items:
                    for item in items:
                        t = (item.inner_text() or "").strip()
                        if t and len(t) > 2:
                            comments.append(t)
                    break
            except:
                continue

        print(f"  Comments found: {len(comments)}")
        if comments:
            print(f"  First: {comments[0][:50]}")

    browser.close()
print("\nDone")
