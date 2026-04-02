"""인테리어 인사이트 관리자 대시보드.

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

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from supabase import create_client

# ── Supabase 연결 ────────────────────────────────────
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
    page_title="인테리어 인사이트 Admin",
    page_icon="📊",
    layout="wide",
)

st.title("📊 인테리어 인사이트 관리자")

# ── 사이드바: 네비게이션 ─────────────────────────────
page = st.sidebar.radio(
    "메뉴",
    ["대시보드", "구독자 관리", "발송 이력", "콘텐츠 확인", "수익"],
    index=0,
)

supabase = get_supabase()


# ══════════════════════════════════════════════════════
# 대시보드
# ══════════════════════════════════════════════════════
if page == "대시보드":
    st.header("대시보드")

    if supabase:
        # 구독자 통계
        subs = supabase.table("subscribers").select("*").eq("is_active", True).execute()
        active_count = len(subs.data) if subs.data else 0

        all_subs = supabase.table("subscribers").select("*").execute()
        total_count = len(all_subs.data) if all_subs.data else 0

        # 최근 발송
        reports = supabase.table("weekly_reports").select("*").order("created_at", desc=True).limit(1).execute()
        last_report = reports.data[0] if reports.data else None

        # 발송 로그
        today = datetime.now().strftime("%Y-%m-%d")
        logs = supabase.table("send_logs").select("*").gte("sent_at", today).execute()
        today_success = sum(1 for l in (logs.data or []) if l.get("status") == "success")
        today_failed = sum(1 for l in (logs.data or []) if l.get("status") == "failed")

        # 수익 계산 (기본 플랜 ₩10,000 가정)
        plan_prices = {"basic": 10000, "pro": 20000}
        monthly_revenue = 0
        for s in (subs.data or []):
            monthly_revenue += plan_prices.get(s.get("plan", "basic"), 10000)

    else:
        active_count = 0
        total_count = 0
        monthly_revenue = 0
        today_success = 0
        today_failed = 0
        last_report = None

    # KPI 카드
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("활성 구독자", f"{active_count}명", f"전체 {total_count}명")
    col2.metric("이번 달 예상 수익", f"₩{monthly_revenue:,}")
    col3.metric("오늘 발송 성공", f"{today_success}건")
    col4.metric("오늘 발송 실패", f"{today_failed}건", delta_color="inverse")

    st.divider()

    # 최근 리포트 정보
    st.subheader("최근 발송 리포트")
    if last_report:
        st.write(f"**기간:** {last_report.get('week_start')} ~ {last_report.get('week_end')}")
        st.write(f"**발송 시각:** {last_report.get('sent_at', '미발송')}")
        st.write(f"**수신자 수:** {last_report.get('recipient_count', 0)}명")
    else:
        st.info("아직 발송된 리포트가 없습니다.")



# ══════════════════════════════════════════════════════
# 구독자 관리
# ══════════════════════════════════════════════════════
elif page == "구독자 관리":
    st.header("👥 구독자 관리")

    if not supabase:
        st.warning("Supabase 연결이 필요합니다. .env에 SUPABASE_URL과 SUPABASE_KEY를 설정하세요.")
        st.stop()

    # 구독자 목록
    response = supabase.table("subscribers").select("*").order("created_at", desc=True).execute()
    subscribers = response.data or []

    if subscribers:
        df = pd.DataFrame(subscribers)
        display_cols = ["email", "name", "company", "plan", "is_active", "created_at"]
        existing_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[existing_cols], use_container_width=True, hide_index=True)

        st.caption(f"총 {len(subscribers)}명 (활성: {sum(1 for s in subscribers if s.get('is_active'))}명)")
    else:
        st.info("등록된 구독자가 없습니다.")

    # 구독자 추가
    st.divider()
    st.subheader("구독자 추가")
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
                    }).execute()
                    st.success(f"구독자 추가 완료: {new_email}")
                    st.rerun()
                except Exception as e:
                    st.error(f"추가 실패: {e}")
            else:
                st.error("이메일은 필수입니다.")

    # 구독자 비활성화
    st.divider()
    st.subheader("구독 해지")
    active_subs = [s for s in subscribers if s.get("is_active")]
    if active_subs:
        emails = [s["email"] for s in active_subs]
        deactivate_email = st.selectbox("해지할 구독자", emails)
        if st.button("구독 해지", type="secondary"):
            sub = next(s for s in active_subs if s["email"] == deactivate_email)
            supabase.table("subscribers").update({"is_active": False}).eq("id", sub["id"]).execute()
            st.success(f"구독 해지 완료: {deactivate_email}")
            st.rerun()


# ══════════════════════════════════════════════════════
# 발송 이력
# ══════════════════════════════════════════════════════
elif page == "발송 이력":
    st.header("📧 발송 이력")

    if supabase:
        # 리포트 목록
        reports = supabase.table("weekly_reports").select("*").order("created_at", desc=True).limit(30).execute()
        report_list = reports.data or []

        if report_list:
            for r in report_list:
                with st.expander(f"📄 {r.get('week_start', '')} ~ {r.get('week_end', '')} | 수신자: {r.get('recipient_count', 0)}명"):
                    st.write(f"**발송 시각:** {r.get('sent_at', '미발송')}")
                    st.write(f"**수신자 수:** {r.get('recipient_count', 0)}명")

                    # 발송 로그
                    logs = supabase.table("send_logs").select("*").eq("report_id", r["id"]).execute()
                    if logs.data:
                        log_df = pd.DataFrame(logs.data)
                        st.dataframe(log_df[["subscriber_id", "status", "error_message", "sent_at"]], hide_index=True)
        else:
            st.info("발송 이력이 없습니다.")
    else:
        st.warning("Supabase 연결 필요")

    # 로컬 발송 로그 (Supabase 없을 때)
    st.divider()
    st.subheader("로컬 로그 파일")
    log_dir = PROJECT_ROOT / "logs"
    if log_dir.exists():
        log_files = sorted(log_dir.glob("daily_*.log"), reverse=True)
        for f in log_files[:10]:
            with st.expander(f"📝 {f.name}"):
                content = f.read_text(encoding="utf-8", errors="replace")
                # 마지막 30줄만
                lines = content.strip().split("\n")
                st.code("\n".join(lines[-30:]), language="text")
    else:
        st.info("로그 파일 없음")


# ══════════════════════════════════════════════════════
# 콘텐츠 확인
# ══════════════════════════════════════════════════════
elif page == "콘텐츠 확인":
    st.header("📑 발급된 콘텐츠 확인")

    # 로컬 리포트 파일 목록
    report_files = sorted(DATA_DIR.glob("report_*.html"), reverse=True)
    analysis_files = sorted(DATA_DIR.glob("analysis_*.json"), reverse=True)

    if report_files:
        selected = st.selectbox(
            "리포트 선택",
            report_files,
            format_func=lambda f: f.name,
        )

        if selected:
            html_content = selected.read_text(encoding="utf-8")

            tab1, tab2 = st.tabs(["미리보기", "분석 데이터"])

            with tab1:
                st.components.v1.html(html_content, height=800, scrolling=True)

            with tab2:
                # 같은 날짜의 분석 JSON 찾기
                date_part = selected.stem.replace("report_", "").replace("report_v5_", "").replace("report_v4_", "")
                matching = [f for f in analysis_files if date_part in f.name]
                if matching:
                    data = json.loads(matching[0].read_text(encoding="utf-8"))
                    st.json(data)
                else:
                    st.info("분석 데이터 없음")
    else:
        st.info("아직 생성된 리포트가 없습니다.")

    # 크롤링 데이터
    st.divider()
    st.subheader("크롤링 데이터")
    crawl_files = sorted(DATA_DIR.glob("crawl_*.json"), reverse=True)
    if crawl_files:
        selected_crawl = st.selectbox(
            "크롤링 데이터 선택",
            crawl_files[:10],
            format_func=lambda f: f"{f.name} ({f.stat().st_size/1024:.0f}KB)",
        )
        if selected_crawl:
            data = json.loads(selected_crawl.read_text(encoding="utf-8"))
            st.write(f"총 {len(data)}건")

            # 게시판별 분포
            boards = {}
            for d in data:
                b = d.get("board", "기타")
                boards[b] = boards.get(b, 0) + 1
            st.bar_chart(pd.Series(boards).sort_values(ascending=False))

            # 샘플
            with st.expander("샘플 데이터 (상위 10건)"):
                for d in data[:10]:
                    st.text(f"[{d.get('board', '')}] {d.get('title', '')}")


# ══════════════════════════════════════════════════════
# 수익
# ══════════════════════════════════════════════════════
elif page == "수익":
    st.header("💰 수익 현황")

    if not supabase:
        st.warning("Supabase 연결 필요")
        st.stop()

    response = supabase.table("subscribers").select("*").execute()
    subscribers = response.data or []

    if not subscribers:
        st.info("구독자가 없습니다.")
        st.stop()

    plan_prices = {"basic": 10000, "pro": 20000}

    # 플랜별 구독자
    active = [s for s in subscribers if s.get("is_active")]
    plan_counts = {}
    for s in active:
        plan = s.get("plan", "basic")
        plan_counts[plan] = plan_counts.get(plan, 0) + 1

    col1, col2, col3 = st.columns(3)
    col1.metric("Basic 구독자", f"{plan_counts.get('basic', 0)}명")
    col2.metric("Pro 구독자", f"{plan_counts.get('pro', 0)}명")

    monthly = sum(plan_prices.get(s.get("plan", "basic"), 10000) for s in active)
    col3.metric("월 예상 수익", f"₩{monthly:,}")

    st.divider()

    # 구독자 추이 (가입일 기준)
    st.subheader("구독자 추이")
    if active:
        df = pd.DataFrame(active)
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"])
            df["month"] = df["created_at"].dt.to_period("M").astype(str)
            monthly_counts = df.groupby("month").size()
            st.line_chart(monthly_counts)

    # 수익 시뮬레이션
    st.divider()
    st.subheader("수익 시뮬레이션")
    sim_basic = st.slider("Basic 구독자 수", 0, 500, plan_counts.get("basic", 0))
    sim_pro = st.slider("Pro 구독자 수", 0, 200, plan_counts.get("pro", 0))
    sim_revenue = sim_basic * plan_prices["basic"] + sim_pro * plan_prices["pro"]
    st.metric("시뮬레이션 월 수익", f"₩{sim_revenue:,}")
    st.metric("시뮬레이션 연 수익", f"₩{sim_revenue * 12:,}")
