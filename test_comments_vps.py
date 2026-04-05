import sys,json,time
sys.path.insert(0,'/opt/idi')
from playwright.sync_api import sync_playwright

COOKIE_FILE='/opt/idi/data/naver_cookies.json'

# 이전에 댓글 수집 성공했던 글 + 실패했던 글 비교
data=json.load(open('/opt/idi/data/crawl_2026-04-04.json'))
with_c=sorted([d for d in data if len(d.get('comments',[]))>0], key=lambda x:-len(x['comments']))[:2]
without_c=[d for d in data if len(d.get('comments',[]))==0 and d.get('content')][:2]

targets=with_c+without_c
print(f"Testing {len(targets)} posts")
for t in targets:
    print(f"  prev={len(t.get('comments',[]))} : {t['title'][:40]}")

# 이 글들의 실제 댓글 수를 네이버에서 직접 확인
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
        print(f"\n{'='*50}")
        print(f"prev={len(t.get('comments',[]))} | {t['title'][:35]}")
        print(f"URL: {t['url']}")

        page.goto(t["url"], wait_until="domcontentloaded", timeout=15000)
        time.sleep(3)

        tgts=[page]+[f for f in page.frames if f != page.main_frame]

        # 모든 frame 스크롤
        for tg in tgts:
            try:
                tg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except:
                pass
        time.sleep(2)
        for tg in tgts:
            try:
                tg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            except:
                pass
        time.sleep(2)

        # 댓글 수 표시 요소 찾기 (댓글이 실제로 있는지)
        for i,frame in enumerate(tgts):
            try:
                # 댓글 수 표시
                count_el=frame.query_selector("[class*='comment_count'], [class*='CommentCount'], .u_cbox_count, [class*='reply_count']")
                if count_el:
                    print(f"  Frame{i} comment_count: {count_el.inner_text()}")
            except:
                pass

            # 댓글 본문
            try:
                items=frame.query_selector_all(".comment_text_box")
                if items:
                    print(f"  Frame{i} .comment_text_box: {len(items)} items")
                    continue
            except:
                pass

            try:
                items=frame.query_selector_all("[class*='comment_text']")
                if items:
                    print(f"  Frame{i} [class*='comment_text']: {len(items)} items")
                    continue
            except:
                pass

            try:
                items=frame.query_selector_all("[class*='Comment']")
                if items:
                    print(f"  Frame{i} [class*='Comment']: {len(items)} items")
            except:
                pass

    browser.close()
print("\nDone")
