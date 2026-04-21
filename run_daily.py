"""Interior Daily Insight — 일일 리포트 전체 파이프라인.

매일 오전 6시 cron으로 실행:
  1. 쿠키로 네이버 카페 크롤링 (본문+댓글)
  2. 유튜브 전문 채널 자막 수집
  3. 카페 데이터 AI 분석 (고인게이지먼트 기반)
  4. 유튜브 데이터 AI 분석
  5. HTML 리포트 생성
  6. Resend로 구독자에게 이메일 발송
"""

import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import anthropic
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

# ── 설정 ──────────────────────────────────────────────
LOG_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"
COOKIE_FILE = DATA_DIR / "naver_cookies.json"
TEMPLATE_DIR = PROJECT_ROOT / "report" / "templates"

CLUB_ID = "23700418"
CAFE_BASE = f"https://cafe.naver.com/f-e/cafes/{CLUB_ID}"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TODAY = datetime.now().strftime("%Y-%m-%d")
TODAY_LABEL = datetime.now().strftime("%Y-%m-%d (%a)")

LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"daily_{TODAY}.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

EXCLUDE_BOARDS = ["(업체가 쓴)", "(광고)"]
CONTENT_SELECTORS = [
    ".se-main-container", ".ContentRenderer", "#postContent",
    ".article_viewer", "#tbody", ".NHN_Writeform_Main",
    "article", "[class*='ArticleContentBox']",
]


# ══════════════════════════════════════════════════════
# STEP 1: 카페 크롤링
# ══════════════════════════════════════════════════════

def create_browser_context(playwright):
    browser = playwright.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        locale="ko-KR",
    )
    if COOKIE_FILE.exists():
        with open(COOKIE_FILE, "r", encoding="utf-8") as f:
            context.add_cookies(json.load(f))
        logger.info("쿠키 로드 완료")
    else:
        logger.error("쿠키 파일 없음. save_cookies.py 실행 필요.")
        browser.close()
        return None, None
    return browser, context


def collect_article_list(page, max_pages=100):
    articles = []
    cutoff = datetime.now() - timedelta(days=1)
    seen_ids = set()
    excluded = 0

    for page_num in range(1, max_pages + 1):
        logger.info(f"목록 {page_num}p (누적 {len(articles)}건)")
        page.goto(f"{CAFE_BASE}/menus/0?viewType=L&page={page_num}")
        time.sleep(random.uniform(1.5, 3.0))

        links = page.query_selector_all("a[href*='/articles/']")
        found_old = False

        for link in links:
            try:
                href = link.get_attribute("href") or ""
                if "commentFocus=true" in href or "referrerAllArticles=false" in href:
                    continue
                match = re.search(r"/articles/(\d+)", href)
                if not match:
                    continue
                aid = match.group(1)
                if aid in seen_ids:
                    continue
                seen_ids.add(aid)

                title = (link.get_attribute("title") or link.inner_text() or "").strip()
                if not title:
                    continue

                row_info = link.evaluate("""el => {
                    let row = el.closest('tr') || el.closest('li') || el.parentElement?.parentElement?.parentElement;
                    if (!row) return {board:'', text:''};
                    let ft = row.querySelector('td:first-child');
                    return {board: ft ? ft.innerText.trim() : '', text: row.innerText || ''};
                }""") or {}

                board = row_info.get("board", "")
                if any(p in board for p in EXCLUDE_BOARDS):
                    excluded += 1
                    continue

                row_text = row_info.get("text", "")
                date_str = ""
                dm = re.search(r"(\d{4}\.\d{2}\.\d{2}\.?)", row_text)
                if dm:
                    date_str = dm.group(1)
                else:
                    tm = re.search(r"\t(\d{1,2}:\d{2})\t", row_text)
                    if tm:
                        date_str = tm.group(1)

                article_date = None
                if re.match(r"^\d{1,2}:\d{2}$", date_str.strip()):
                    article_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    for fmt in ["%Y.%m.%d.", "%Y.%m.%d"]:
                        try:
                            article_date = datetime.strptime(date_str.strip(), fmt)
                            break
                        except ValueError:
                            continue

                if article_date and article_date < cutoff:
                    found_old = True
                    break

                articles.append({
                    "article_id": aid, "title": title, "board": board,
                    "date_str": date_str, "url": f"{CAFE_BASE}/articles/{aid}",
                })
            except Exception:
                continue

        if found_old:
            logger.info("어제 게시글 도달 — 수집 종료")
            break
        if not links and page_num > 3:
            break

    logger.info(f"목록 수집 완료: {len(articles)}건 (업체글 {excluded}건 제외)")
    return articles


def collect_content(page, articles):
    total = len(articles)
    ok = 0
    start = time.time()

    for i, article in enumerate(articles):
        try:
            page.goto(article["url"], wait_until="domcontentloaded", timeout=15000)
            time.sleep(random.uniform(2.0, 3.0))

            targets = [page] + [f for f in page.frames if f != page.main_frame]

            # 메인 페이지 + 모든 iframe 스크롤 (댓글 로딩)
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

            # 본문 수집
            content = ""
            for target in targets:
                if content:
                    break
                for sel in CONTENT_SELECTORS:
                    try:
                        el = target.query_selector(sel)
                        if el:
                            text = (el.inner_text() or "").strip()
                            if len(text) > 20:
                                content = text
                                break
                    except:
                        continue

            # 댓글 수집 — Frame1(iframe)에서 주로 발견됨
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

            article["content"] = content
            article["comments"] = comments
            if content:
                ok += 1
        except Exception:
            article["content"] = ""
            article["comments"] = []

        if (i + 1) % 50 == 0:
            elapsed = time.time() - start
            remaining = (total - i - 1) / ((i + 1) / elapsed) if elapsed > 0 else 0
            logger.info(f"  [{i+1}/{total}] 본문:{ok}건 | 남은시간: {remaining/60:.0f}분")

    logger.info(f"본문 수집 완료: {ok}/{total}건")
    return articles


# ══════════════════════════════════════════════════════
# STEP 2: 유튜브 수집
# ══════════════════════════════════════════════════════

def collect_youtube():
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY 미설정 — 유튜브 수집 생략")
        return []

    from collector.youtube_collector import collect_youtube as yt_collect
    try:
        videos = yt_collect(YOUTUBE_API_KEY, days_back=1)
        return videos
    except Exception as e:
        logger.error(f"유튜브 수집 실패: {e}")
        return []


# ══════════════════════════════════════════════════════
# STEP 3: 카페 분석 (고인게이지먼트 기반)
# ══════════════════════════════════════════════════════

def analyze_cafe(posts):
    from processor.signal_extractor import filter_high_engagement, build_analysis_text

    high = filter_high_engagement(posts, min_comments=5)
    aggregated = build_analysis_text(posts, high)
    logger.info(f"분석용 텍스트: {len(aggregated):,}자 (고인게이지먼트 {len(high)}건)")

    SYSTEM_PROMPT = """당신은 연간 수천만 원의 컨설팅 피를 받는 인테리어 업계 비즈니스 인텔리전스 애널리스트입니다.

독자: 소형 인테리어 시공업체 대표, 프리랜서 인테리어 디자이너.
이들은 직접 시공하거나, 고객에게 인테리어를 제안하고 시공하는 사람들입니다.
이들은 제품 제조사가 아닙니다. 소파 회사도, 제습기 회사도, 가구 회사도 아닙니다.

분석 원칙:
- 댓글이 많은 게시글이 시장의 진짜 시그널입니다.
- "필름시공", "턴키" 같은 범용 키워드가 아니라, "영림 PS170", "디아망 회크화" 같은 구체적 제품명/모델명을 추출하십시오.
- 소비자가 비교하는 제품 조합(A vs B)을 찾아내십시오.
- 견적/가격이 언급된 경우 반드시 구체적 금액(만원 단위)을 포함하십시오. "견적 다수 문의" 같은 애매한 표현 금지.
- 업체명이 추천되거나 불만 대상이 된 경우 반드시 포함하십시오.

인사이트(action) 작성 원칙 (매우 중요):
- 모든 인사이트는 "인테리어 시공업체가 이 정보를 어떻게 활용할 수 있는가" 관점에서 작성하십시오.
- 제품이 뜨고 있다면 → "고객 제안 시 이 제품을 참고해보시면 좋겠습니다", "이 제품의 시공 사례를 살펴보시는 것을 권장합니다"
- 소파/가구/가전이 뜨고 있다면 → "이 제품과 어울리는 공간 연출을 고려해보실 만합니다"
- 절대로 해당 제품의 제조사/판매사에게 하는 조언을 쓰지 마십시오.
- 데이터에서 확실히 드러나지 않는 내용을 확정적으로 단언하지 마십시오.

톤 (매우 중요):
- 확정적 지시("~하십시오", "~강화하십시오")가 아니라, 가벼운 제안 톤으로 작성.
- "~에 주목해보실 만합니다", "~를 살펴보시는 것을 권장합니다", "~를 고려해보시면 좋겠습니다", "~한 흐름이 감지되고 있습니다"
- 이런 키워드가 있으니 한번 살펴보시라는 느낌으로. 강압적이지 않게.
소비자 발언 인용 시 반드시 재구성하여 작성.
응답: 순수 JSON만."""

    USER_PROMPT = f"""아래는 {TODAY} 네이버 '셀프인테리어' 카페 {len(posts)}개 게시글입니다.
고인게이지먼트 {len(high)}건은 본문+댓글 포함, 나머지는 제목만.

{aggregated}

---

중요: section1, section6은 필수. section2~5는 데이터 있을 때만. 없으면 빈 배열.

{{
  "meta": {{"date": "{TODAY}", "total_posts": {len(posts)}, "high_engagement_posts": {len(high)}, "generated_at": "{datetime.now().strftime('%Y-%m-%d %H:%M')}"}},
  "section1_hot_products": {{
    "title": "오늘의 소비자 시그널 TOP 10",
    "products": [
      {{"rank": 1, "product": "브랜드 제품명", "category": "카테고리", "signal_tag": "강추|불만|수급이슈|비교중|신제품", "one_line": "핵심 시그널 한 줄", "action": "업체 대응 인사이트 2~3문장. 존댓말."}}
    ]
  }},
  "section2_product_battles": {{
    "title": "소비자가 비교하고 있는 것",
    "battles": [{{"product_a": "A", "product_b": "B", "category": "카테고리", "context": "비교 배경 1줄", "action": "업체 대응 2~3문장."}}]
  }},
  "section4_consumer_pain": {{
    "title": "소비자 불만 시그널",
    "pains": [{{"headline": "문제 핵심", "severity": "심각|주의|참고", "detail": "상황 1~2문장(재구성)", "action": "예방법 2~3문장."}}]
  }},
  "section5_market_signal": {{
    "title": "마켓 시그널",
    "signals": [{{"headline": "시그널 핵심", "detail": "상황 1~2문장(재구성)", "impact": "업체 영향 1줄", "action": "대응 2~3문장."}}]
  }},
  "section6_one_action": {{
    "title": "오늘의 액션",
    "action": "구체적 행동 (~하십시오)",
    "why": "근거 1줄",
    "how": "실행법 3단계를 하나의 문자열로 작성. 예: '1) 첫번째 2) 두번째 3) 세번째' 형태. 리스트([])가 아닌 문자열로."
  }}
}}"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT}],
    )

    raw = message.content[0].text.strip()
    if "```json" in raw:
        raw = raw[raw.index("```json")+7:raw.index("```", raw.index("```json")+7)]
    elif "```" in raw:
        raw = raw[raw.index("```")+3:raw.index("```", raw.index("```")+3)]
    return json.loads(raw.strip())


# ══════════════════════════════════════════════════════
# STEP 4: 유튜브 분석
# ══════════════════════════════════════════════════════

def analyze_youtube(videos):
    with_transcript = [v for v in videos if v.get("has_transcript")]
    if not with_transcript:
        logger.info("자막 있는 영상 없음 — 유튜브 분석 생략")
        return None

    lines = []
    for i, v in enumerate(with_transcript):
        transcript = v.get("transcript", "")[:2000]
        if len(v.get("transcript", "")) > 2000:
            transcript += "..."
        lines.append(f"\n--- [video_id: {v['video_id']}] {v['channel']} ---")
        lines.append(f"제목: {v['title']}")
        lines.append(f"자막: {transcript}")

    aggregated = "\n".join(lines)

    SYSTEM_PROMPT = """인테리어 업계 비즈니스 인텔리전스 애널리스트. 유튜브 인테리어 전문 채널 분석.
톤: 전문 컨설턴트 존댓말. 응답: 순수 JSON만."""

    USER_PROMPT = f"""오늘 인테리어 유튜브 영상 {len(with_transcript)}건 자막:

{aggregated}

---

{{
  "featured_videos": [
    {{"video_id": "위 데이터의 video_id 그대로", "channel": "채널명", "title": "제목", "summary": "핵심 2~3문장. 제품명/시공법/가격 포함.", "business_value": "업체에게 중요한 이유 1줄", "keywords": ["구매 가능한 특정 상품명만. 일반 명사 제외. 없으면 빈 배열."]}}
  ],
  "overall_insight": {{
    "title": "오늘의 유튜브 종합 인사이트",
    "insight": "전체 종합 2~3문장. 존댓말.",
    "action": "업체 행동 1줄. 존댓말."
  }}
}}"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT}],
    )

    raw = message.content[0].text.strip()
    if "```json" in raw:
        raw = raw[raw.index("```json")+7:raw.index("```", raw.index("```json")+7)]
    elif "```" in raw:
        raw = raw[raw.index("```")+3:raw.index("```", raw.index("```")+3)]
    return json.loads(raw.strip())


# ══════════════════════════════════════════════════════
# STEP 5: HTML 리포트 생성
# ══════════════════════════════════════════════════════

def generate_report(analysis, youtube_analysis=None):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("daily_v6.html")
    return template.render(
        analysis=analysis,
        meta=analysis["meta"],
        youtube=youtube_analysis,
        report_date=TODAY_LABEL,
        unsubscribe_url="#",
    )


# ══════════════════════════════════════════════════════
# STEP 6: 이메일 발송
# ══════════════════════════════════════════════════════

def get_subscribers():
    """Supabase에서 활성 구독자 이메일 목록을 가져온다."""
    # 테스트 모드: TEST_MODE=1 이면 구독자 조회 건너뛰고 TEST_EMAIL 로만 발송
    if os.getenv("TEST_MODE") == "1":
        test = os.getenv("TEST_EMAIL", "")
        emails = [e.strip() for e in test.split(",") if e.strip()]
        logger.info(f"TEST_MODE 활성 — 실제 구독자 건너뛰고 TEST_EMAIL 로만 발송: {emails}")
        return emails

    if not SUPABASE_URL or "placeholder" in SUPABASE_URL:
        # Supabase 미설정 시 테스트 이메일
        test = os.getenv("TEST_EMAIL", "")
        return [e.strip() for e in test.split(",") if e.strip()]

    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = sb.table("subscribers").select("email").eq("is_active", True).execute()
        emails = [s["email"] for s in (response.data or [])]
        logger.info(f"활성 구독자: {len(emails)}명")
        return emails
    except Exception as e:
        logger.error(f"구독자 조회 실패: {e}")
        # 폴백: TEST_EMAIL로 발송
        test = os.getenv("TEST_EMAIL", "")
        fallback = [e.strip() for e in test.split(",") if e.strip()]
        if fallback:
            logger.info(f"TEST_EMAIL 폴백: {fallback}")
        return fallback


def send_emails(html, to_emails):
    """Resend로 이메일 발송."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY 미설정 — 이메일 발송 생략")
        return

    from mailer.resend_mailer import ResendMailer
    mailer = ResendMailer(api_key=RESEND_API_KEY)
    subject = f"[Interior Daily Insight] 오늘의 인사이트가 도착하였습니다"
    result = mailer.send_batch(to_emails, subject, html)
    logger.info(f"발송: 성공 {result['success']}, 실패 {result['failed']}")


# ══════════════════════════════════════════════════════
# 메인 파이프라인
# ══════════════════════════════════════════════════════

def main():
    logger.info("=" * 60)
    logger.info(f"Interior Daily Insight 파이프라인 시작: {TODAY}")
    logger.info("=" * 60)
    pipeline_start = time.time()

    # 1. 카페 크롤링
    logger.info("[1/7] 카페 게시글 목록 수집")
    with sync_playwright() as p:
        browser, context = create_browser_context(p)
        if not browser:
            return

        page = context.new_page()
        page.goto("https://cafe.naver.com/overseer")
        time.sleep(3)
        if "login" in page.url.lower():
            logger.error("쿠키 만료. save_cookies.py 실행 필요.")
            browser.close()
            return

        articles = collect_article_list(page)
        if not articles:
            logger.error("수집된 게시글 없음. 중단.")
            browser.close()
            return

        logger.info(f"[2/7] 본문+댓글 수집 ({len(articles)}건)")
        articles = collect_content(page, articles)
        browser.close()

    crawl_file = DATA_DIR / f"crawl_{TODAY}.json"
    with open(crawl_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"크롤링 저장: {crawl_file}")

    # 2. 유튜브 수집
    logger.info("[3/7] 유튜브 채널 수집")
    yt_videos = collect_youtube()

    # 3. 카페 분석
    logger.info("[4/7] 카페 AI 분석")
    try:
        cafe_analysis = analyze_cafe(articles)
    except Exception as e:
        logger.error(f"카페 분석 실패: {e}")
        return

    with open(DATA_DIR / f"analysis_{TODAY}.json", "w", encoding="utf-8") as f:
        json.dump(cafe_analysis, f, ensure_ascii=False, indent=2)

    # 4. 유튜브 분석
    logger.info("[5/7] 유튜브 AI 분석")
    yt_analysis = None
    if yt_videos:
        try:
            yt_analysis = analyze_youtube(yt_videos)
            with open(DATA_DIR / f"youtube_analysis_{TODAY}.json", "w", encoding="utf-8") as f:
                json.dump(yt_analysis, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"유튜브 분석 실패: {e}")

    # 5. 리포트 생성
    logger.info("[6/7] HTML 리포트 생성")
    html = generate_report(cafe_analysis, yt_analysis)
    report_file = DATA_DIR / f"report_{TODAY}.html"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"리포트 저장: {report_file}")

    # 6. 이메일 발송 — KST 07:00까지 대기 후 발송
    import pytz
    kst = pytz.timezone("Asia/Seoul")
    now_kst = datetime.now(pytz.utc).astimezone(kst)
    target_hour = 7
    if now_kst.hour < target_hour:
        wait_until = now_kst.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        wait_seconds = (wait_until - now_kst).total_seconds()
        logger.info(f"KST {target_hour}시까지 {wait_seconds/60:.0f}분 대기...")
        time.sleep(wait_seconds)

    logger.info("[7/7] 이메일 발송")
    subscribers = get_subscribers()
    if subscribers:
        send_emails(html, subscribers)
    else:
        logger.info("발송 대상 없음")

    # 완료
    elapsed = time.time() - pipeline_start
    logger.info("=" * 60)
    logger.info(f"파이프라인 완료! {elapsed/60:.1f}분 소요")
    logger.info(f"  카페: {len(articles)}건 | 유튜브: {len(yt_videos)}건")
    logger.info(f"  리포트: {report_file}")
    logger.info(f"  발송: {len(subscribers)}명")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
