-- 인테리어 인사이트 위클리 - 데이터베이스 스키마
-- Supabase (PostgreSQL) 용

-- 구독자 테이블
CREATE TABLE subscribers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    company TEXT,
    plan TEXT DEFAULT 'basic' CHECK (plan IN ('basic', 'pro')),
    stripe_customer_id TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 주간 리포트 테이블
CREATE TABLE weekly_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    raw_posts JSONB,
    analysis JSONB,
    html_content TEXT,
    sent_at TIMESTAMPTZ,
    recipient_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 발송 로그 테이블
CREATE TABLE send_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID REFERENCES weekly_reports(id),
    subscriber_id UUID REFERENCES subscribers(id),
    status TEXT CHECK (status IN ('success', 'failed', 'pending')),
    error_message TEXT,
    sent_at TIMESTAMPTZ DEFAULT now()
);

-- 수집 로그 테이블
CREATE TABLE collection_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT NOT NULL,
    post_count INT DEFAULT 0,
    status TEXT CHECK (status IN ('success', 'failed')),
    error_message TEXT,
    collected_at TIMESTAMPTZ DEFAULT now()
);

-- 인덱스
CREATE INDEX idx_subscribers_active ON subscribers(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_reports_week ON weekly_reports(week_start, week_end);
CREATE INDEX idx_send_logs_report ON send_logs(report_id);

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER subscribers_updated_at
    BEFORE UPDATE ON subscribers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
