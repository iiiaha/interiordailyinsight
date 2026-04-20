"""Interior Daily Insight — 관리자 대시보드.

실행: streamlit run admin/dashboard.py
접속: http://localhost:8501
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

DATA_DIR = PROJECT_ROOT / "data"


@st.cache_resource
def get_supabase():
    if not SUPABASE_URL or "placeholder" in SUPABASE_URL:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ── 페이지 설정 ──────────────────────────────────────
st.set_page_config(
    page_title="Interior Daily Insight · Admin",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 브랜드 CSS ───────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');

:root {
  --bg: #F5F3EF;
  --bg-card: #FFFFFF;
  --bg-soft: #EDEAE4;
  --olive: #3D4A3C;
  --olive-light: #4A5A49;
  --charcoal: #2C2C2C;
  --text: #3A3A3A;
  --text-sub: #7A7A72;
  --border: #D5D0C8;
  --danger: #8B3A3A;
  --success: #0F766E;
}
html, body, [class*="css"], .stMarkdown, p, span, div, li, label {
  font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
  color: var(--text);
}
h1, h2, h3, h4 {
  font-family: 'Playfair Display', Georgia, serif !important;
  color: var(--charcoal) !important;
  letter-spacing: -0.5px;
}
section[data-testid="stSidebar"] {
  background: var(--bg-soft) !important;
  border-right: 1px solid var(--border);
}
.app-header {
  padding: 8px 0 24px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
}
.app-header .brand {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 24px; font-weight: 700; color: var(--charcoal);
  letter-spacing: -0.5px;
}
.app-header .tagline {
  font-size: 12px; color: var(--text-sub); letter-spacing: 3px;
  text-transform: uppercase; margin-top: 4px;
}
.kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  padding: 24px;
  border-radius: 4px;
  transition: all 0.2s;
}
.kpi-card:hover {
  box-shadow: 0 4px 20px rgba(61,74,60,0.08);
  transform: translateY(-1px);
}
.kpi-card .label {
  font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
  color: var(--text-sub); font-weight: 600; margin-bottom: 12px;
}
.kpi-card .value {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 36px; font-weight: 700; color: var(--charcoal);
  line-height: 1;
}
.kpi-card .value small {
  font-size: 16px; color: var(--text-sub); font-weight: 400; margin-left: 4px;
}
.kpi-card .delta {
  font-size: 12px; color: var(--text-sub); margin-top: 10px;
}
.kpi-card .delta.up { color: var(--success); }
.kpi-card .delta.down { color: var(--danger); }
.overline {
  font-size: 11px; letter-spacing: 3px; text-transform: uppercase;
  color: var(--olive); font-weight: 600; margin-bottom: 8px;
}
.stButton > button {
  background: var(--olive) !important;
  color: white !important;
  border: none !important;
  border-radius: 4px !important;
  font-weight: 600 !important;
  letter-spacing: 0.5px !important;
}
.stButton > button:hover {
  background: var(--olive-light) !important;
  box-shadow: 0 4px 12px rgba(61,74,60,0.2);
}
.stDataFrame {
  border: 1px solid var(--border);
  border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str = "", delta_type: str = ""):
    """커스텀 KPI 카드 렌더링."""
    delta_html = f'<div class="delta {delta_type}">{delta}</div>' if delta else ""
    st.markdown(f"""
    <div class="kpi-card">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
      {delta_html}
    </div>
    """, unsafe_allow_html=True)


# ── 상단 타이틀 ──────────────────────────────────────
st.markdown("""
<div class="app-header">
  <div class="brand">Interior Daily Insight</div>
  <div class="tagline">Admin Console</div>
</div>
""", unsafe_allow_html=True)

# ── 사이드바 ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### 메뉴")
    page = st.radio(
        "페이지",
        ["대시보드", "구독자", "발송 이력", "콘텐츠", "통계"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

supabase = get_supabase()


# ══════════════════════════════════════════════════════
# 대시보드
# ══════════════════════════════════════════════════════
if page == "대시보드":
    st.markdown('<p class="overline">Overview</p>', unsafe_allow_html=True)
    st.markdown("## 오늘의 현황")
    st.write("")

    if supabase:
        subs = supabase.table("subscribers").select("*").eq("is_active", True).execute()
        active_count = len(subs.data) if subs.data else 0

        all_subs = supabase.table("subscribers").select("*").execute()
        total_count = len(all_subs.data) if all_subs.data else 0

        # 오늘 가입자
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_new = sum(1 for s in (all_subs.data or []) if s.get("created_at", "").startswith(today_str))

        # 최근 7일 가입자
        week_ago = (datetime.now() - timedelta(days=7)).date()
        week_new = sum(
            1 for s in (all_subs.data or [])
            if s.get("created_at") and pd.to_datetime(s["created_at"]).date() >= week_ago
        )

        # 발송 로그
        logs = supabase.table("send_logs").select("*").gte("sent_at", today_str).execute()
        today_success = sum(1 for l in (logs.data or []) if l.get("status") == "success")
        today_failed = sum(1 for l in (logs.data or []) if l.get("status") == "failed")

        reports = supabase.table("weekly_reports").select("*").order("created_at", desc=True).limit(1).execute()
        last_report = reports.data[0] if reports.data else None
    else:
        active_count = total_count = today_new = week_new = today_success = today_failed = 0
        last_report = None

    # KPI 4개
    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1:
        kpi_card("Active Subscribers", f"{active_count}<small>명</small>", f"전체 {total_count}명")
    with col2:
        kpi_card("오늘 가입", f"+{today_new}<small>명</small>", f"최근 7일 +{week_new}명")
    with col3:
        kpi_card("오늘 발송 성공", f"{today_success}<small>건</small>", "", "up")
    with col4:
        kpi_card("오늘 발송 실패", f"{today_failed}<small>건</small>", "", "down" if today_failed else "")

    st.write("")
    st.write("")

    # 최근 리포트
    st.markdown('<p class="overline">Latest Report</p>', unsafe_allow_html=True)
    st.markdown("### 최근 발송 리포트")
    if last_report:
        col_a, col_b, col_c = st.columns(3)
        col_a.markdown(f"**기간**  \n{last_report.get('week_start','-')} ~ {last_report.get('week_end','-')}")
        col_b.markdown(f"**발송 시각**  \n{last_report.get('sent_at', '미발송')}")
        col_c.markdown(f"**수신자**  \n{last_report.get('recipient_count', 0)}명")
    else:
        st.info("아직 발송된 리포트가 없습니다.")


# ══════════════════════════════════════════════════════
# 구독자
# ══════════════════════════════════════════════════════
elif page == "구독자":
    st.markdown('<p class="overline">Subscribers</p>', unsafe_allow_html=True)
    st.markdown("## 구독자 관리")
    st.write("")

    if not supabase:
        st.warning("Supabase 연결이 필요합니다. .env 확인 후 재실행해주세요.")
        st.stop()

    response = supabase.table("subscribers").select("*").order("created_at", desc=True).execute()
    subscribers = response.data or []

    # 요약 3개
    active_n = sum(1 for s in subscribers if s.get("is_active"))
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_new = sum(1 for s in subscribers if s.get("created_at", "").startswith(today_str))

    col1, col2, col3 = st.columns(3, gap="medium")
    with col1: kpi_card("전체 구독자", f"{len(subscribers)}<small>명</small>")
    with col2: kpi_card("활성", f"{active_n}<small>명</small>")
    with col3: kpi_card("오늘 가입", f"+{today_new}<small>명</small>")

    st.write("")
    st.write("")

    # 검색
    st.markdown('<p class="overline">List</p>', unsafe_allow_html=True)
    st.markdown("### 전체 목록")
    search = st.text_input("이메일 또는 이름 검색", placeholder="검색어 입력…", label_visibility="collapsed")

    filtered = subscribers
    if search:
        q = search.lower()
        filtered = [
            s for s in subscribers
            if q in (s.get("email") or "").lower() or q in (s.get("name") or "").lower()
        ]

    if filtered:
        df = pd.DataFrame(filtered)
        display_cols = ["email", "name", "company", "plan", "is_active", "created_at"]
        existing_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(
            df[existing_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "email": "이메일",
                "name": "이름",
                "company": "회사",
                "plan": "플랜",
                "is_active": st.column_config.CheckboxColumn("활성"),
                "created_at": st.column_config.DatetimeColumn("가입일시", format="YYYY-MM-DD HH:mm"),
            },
        )
        st.caption(f"{len(filtered)}명 표시 / 전체 {len(subscribers)}명 (활성 {active_n}명)")
    else:
        st.info("조건에 맞는 구독자가 없습니다.")

    st.write("")

    # 수동 추가
    with st.expander("✏️  구독자 수동 추가"):
        with st.form("add_subscriber"):
            col1, col2 = st.columns(2)
            new_email = col1.text_input("이메일 *")
            new_name = col2.text_input("이름")
            col3, col4 = st.columns(2)
            new_company = col3.text_input("회사명")
            new_plan = col4.selectbox("플랜", ["basic", "pro"])
            if st.form_submit_button("추가"):
                if new_email:
                    try:
                        supabase.table("subscribers").insert({
                            "email": new_email,
                            "name": new_name or None,
                            "company": new_company or None,
                            "plan": new_plan,
                            "is_active": True,
                        }).execute()
                        st.success(f"추가 완료: {new_email}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"추가 실패: {e}")
                else:
                    st.error("이메일은 필수입니다.")

    # 해지
    active_subs = [s for s in subscribers if s.get("is_active")]
    if active_subs:
        with st.expander("🚫  구독 해지"):
            emails = [s["email"] for s in active_subs]
            deactivate_email = st.selectbox("해지할 구독자", emails, key="deactivate")
            if st.button("구독 해지", type="secondary"):
                sub = next(s for s in active_subs if s["email"] == deactivate_email)
                supabase.table("subscribers").update({"is_active": False}).eq("id", sub["id"]).execute()
                st.success(f"해지 완료: {deactivate_email}")
                st.rerun()


# ══════════════════════════════════════════════════════
# 발송 이력
# ══════════════════════════════════════════════════════
elif page == "발송 이력":
    st.markdown('<p class="overline">Send History</p>', unsafe_allow_html=True)
    st.markdown("## 발송 이력")
    st.write("")

    if supabase:
        reports = supabase.table("weekly_reports").select("*").order("created_at", desc=True).limit(30).execute()
        report_list = reports.data or []

        if report_list:
            for r in report_list:
                header = f"📄  {r.get('week_start', '')} ~ {r.get('week_end', '')}  ·  수신자 {r.get('recipient_count', 0)}명"
                with st.expander(header):
                    col1, col2 = st.columns(2)
                    col1.markdown(f"**발송 시각**  \n{r.get('sent_at', '미발송')}")
                    col2.markdown(f"**수신자 수**  \n{r.get('recipient_count', 0)}명")

                    logs = supabase.table("send_logs").select("*").eq("report_id", r["id"]).execute()
                    if logs.data:
                        log_df = pd.DataFrame(logs.data)
                        cols = [c for c in ["subscriber_id", "status", "error_message", "sent_at"] if c in log_df.columns]
                        st.dataframe(log_df[cols], hide_index=True, use_container_width=True)
        else:
            st.info("DB에 발송 이력이 없습니다.")
    else:
        st.warning("Supabase 연결 필요")

    st.write("")

    # 로컬 로그
    st.markdown('<p class="overline">Local Logs</p>', unsafe_allow_html=True)
    st.markdown("### 로컬 로그 파일")
    log_dir = PROJECT_ROOT / "logs"
    if log_dir.exists():
        log_files = sorted(log_dir.glob("daily_*.log"), reverse=True)
        if log_files:
            for f in log_files[:10]:
                with st.expander(f"📝  {f.name}"):
                    content = f.read_text(encoding="utf-8", errors="replace")
                    lines = content.strip().split("\n")
                    st.code("\n".join(lines[-30:]), language="text")
        else:
            st.info("로그 파일 없음")
    else:
        st.info("logs 디렉토리 없음")


# ══════════════════════════════════════════════════════
# 콘텐츠
# ══════════════════════════════════════════════════════
elif page == "콘텐츠":
    st.markdown('<p class="overline">Content</p>', unsafe_allow_html=True)
    st.markdown("## 발급된 콘텐츠 확인")
    st.write("")

    report_files = sorted(DATA_DIR.glob("report_*.html"), reverse=True)
    analysis_files = sorted(DATA_DIR.glob("analysis_*.json"), reverse=True)

    if report_files:
        selected = st.selectbox("리포트 선택", report_files, format_func=lambda f: f.name)

        if selected:
            html_content = selected.read_text(encoding="utf-8")
            tab1, tab2 = st.tabs(["미리보기", "분석 데이터"])

            with tab1:
                st.components.v1.html(html_content, height=900, scrolling=True)

            with tab2:
                date_part = selected.stem.replace("report_", "").replace("report_v5_", "").replace("report_v4_", "")
                matching = [f for f in analysis_files if date_part in f.name]
                if matching:
                    data = json.loads(matching[0].read_text(encoding="utf-8"))
                    st.json(data)
                else:
                    st.info("분석 데이터 없음")
    else:
        st.info("아직 생성된 리포트가 없습니다.")

    st.write("")

    # 크롤링
    st.markdown('<p class="overline">Crawl Data</p>', unsafe_allow_html=True)
    st.markdown("### 크롤링 데이터")
    crawl_files = sorted(DATA_DIR.glob("crawl_*.json"), reverse=True)
    if crawl_files:
        selected_crawl = st.selectbox(
            "크롤링 선택",
            crawl_files[:10],
            format_func=lambda f: f"{f.name}  ·  {f.stat().st_size/1024:.0f}KB",
        )
        if selected_crawl:
            data = json.loads(selected_crawl.read_text(encoding="utf-8"))
            st.caption(f"총 {len(data)}건")

            boards = {}
            for d in data:
                b = d.get("board", "기타")
                boards[b] = boards.get(b, 0) + 1
            st.bar_chart(pd.Series(boards).sort_values(ascending=False))

            with st.expander("샘플 (상위 10건)"):
                for d in data[:10]:
                    st.text(f"[{d.get('board', '')}]  {d.get('title', '')}")


# ══════════════════════════════════════════════════════
# 통계 (무료 전환으로 기존 '수익' 섹션 개편)
# ══════════════════════════════════════════════════════
elif page == "통계":
    st.markdown('<p class="overline">Analytics</p>', unsafe_allow_html=True)
    st.markdown("## 구독 통계")
    st.write("")

    if not supabase:
        st.warning("Supabase 연결 필요")
        st.stop()

    response = supabase.table("subscribers").select("*").execute()
    subscribers = response.data or []

    if not subscribers:
        st.info("아직 구독자가 없습니다.")
        st.stop()

    active = [s for s in subscribers if s.get("is_active")]
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_new = sum(1 for s in subscribers if s.get("created_at", "").startswith(today_str))
    week_ago = (datetime.now() - timedelta(days=7)).date()
    week_new = sum(
        1 for s in subscribers
        if s.get("created_at") and pd.to_datetime(s["created_at"]).date() >= week_ago
    )
    churn_rate = (len(subscribers) - len(active)) / len(subscribers) * 100 if subscribers else 0

    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1: kpi_card("전체 구독자", f"{len(subscribers)}<small>명</small>")
    with col2: kpi_card("활성 구독자", f"{len(active)}<small>명</small>")
    with col3: kpi_card("이번 주 신규", f"+{week_new}<small>명</small>", f"오늘 +{today_new}명")
    with col4: kpi_card("해지율", f"{churn_rate:.1f}<small>%</small>")

    st.write("")
    st.write("")

    # 가입 추이
    st.markdown('<p class="overline">Growth</p>', unsafe_allow_html=True)
    st.markdown("### 가입자 추이")

    df = pd.DataFrame(subscribers)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["date"] = df["created_at"].dt.date
        daily = df.groupby("date").size().rename("신규 가입")
        # 누적
        cumulative = daily.cumsum().rename("누적")
        chart_df = pd.concat([daily, cumulative], axis=1)
        st.line_chart(chart_df, height=280)

    st.write("")

    # 회사별 분포 (선택)
    st.markdown('<p class="overline">Company</p>', unsafe_allow_html=True)
    st.markdown("### 회사별 분포")
    companies = [s.get("company") for s in active if s.get("company")]
    if companies:
        comp_df = pd.Series(companies).value_counts().head(10)
        st.bar_chart(comp_df, height=260)
    else:
        st.caption("회사 정보 입력한 구독자가 아직 없습니다.")
