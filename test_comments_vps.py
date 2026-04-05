import sys,json,time
sys.path.insert(0,'/opt/idi')
from playwright.sync_api import sync_playwright

COOKIE_FILE='/opt/idi/data/naver_cookies.json'

# 댓글 수집됐던 글 중 가장 많은 것 3개
data=json.load(open('/opt/idi/data/crawl_2026-04-04.json'))
with_comments=sorted([d for d in data if len(d.get('comments',[]))>0], key=lambda x:-len(x['comments']))
targets=with_comments[:3]
print(f"Testing {len(targets)} posts (with most comments)")
for t in targets:
    print(f"  {len(t['comments'])} comments: {t['title'][:40]}")

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

    # 댓글 0개였던 글도 1개 테스트
    no_comments=[d for d in data if len(d.get('comments',[]))==0 and d.get('content')]
    targets.append(no_comments[0])
    print(f"\n+ 1 post with 0 comments: {no_comments[0]['title'][:40]}")

    for t in targets:
        url=t['url']
        title=t['title'][:30]
        prev_comments=len(t.get('comments',[]))
        print(f"\n{'='*50}")
        print(f"{title} (prev: {prev_comments} comments)")
        print(f"URL: {url}")

        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(2)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)

        print(f"Frames: {len(page.frames)}")

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
        ]

        found=False
        for i,frame in enumerate(page.frames):
            for sel in all_selectors:
                try:
                    items=frame.query_selector_all(sel)
                    if items and len(items)>0:
                        texts=[item.inner_text()[:50] for item in items[:2]]
                        print(f"  HIT Frame{i} '{sel}': {len(items)} items")
                        for tx in texts:
                            print(f"    > {tx}")
                        found=True
                except:
                    continue
            if found:
                break

        if not found:
            print("  NO COMMENTS FOUND with any selector")

    browser.close()
print("\nDone")
