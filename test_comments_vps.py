import sys,json,time
sys.path.insert(0,'/opt/idi')
from playwright.sync_api import sync_playwright

COOKIE_FILE='/opt/idi/data/naver_cookies.json'
CONTENT_SELECTORS = [
    ".se-main-container", ".ContentRenderer", "#postContent",
    ".article_viewer", "#tbody", ".NHN_Writeform_Main",
    "article", "[class*='ArticleContentBox']",
]

# 오늘 수집된 데이터에서 댓글 많을 것 같은 글 3개 가져오기
data=json.load(open('/opt/idi/data/crawl_2026-04-04.json'))
# 본문 있는 글 중 앞에서 3개
targets=[d for d in data if d.get('content')][:3]
print(f"Testing {len(targets)} posts")

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

    for t in targets:
        url=t['url']
        title=t['title'][:30]
        print(f"\n--- {title} ---")
        print(f"URL: {url}")

        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)

        # 스크롤 테스트
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)

        # 모든 frame 정보
        print(f"Frames: {len(page.frames)}")
        for i,frame in enumerate(page.frames):
            furl=frame.url[:80]
            print(f"  Frame {i}: {furl}")

        # 댓글 selector 테스트 - 모든 frame에서
        all_selectors = [
            ".comment_text_box",
            ".u_cbox_text_wrap",
            "[class*='comment_text']",
            "[class*='CommentItem']",
            ".txt_comment",
            ".comment_inbox .text_comment",
            ".u_cbox_contents",
            ".u_cbox_comment_box",
            "[class*='comment']",
            "[class*='Comment']",
            "[class*='reply']",
        ]

        for i,frame in enumerate(page.frames):
            for sel in all_selectors:
                try:
                    items=frame.query_selector_all(sel)
                    if items:
                        texts=[item.inner_text()[:50] for item in items[:3]]
                        print(f"  FOUND Frame{i} '{sel}': {len(items)} items")
                        for tx in texts:
                            print(f"    > {tx}")
                        break
                except:
                    continue

    browser.close()
print("\nDone")
