-- RLS 활성화 및 최소 정책
-- 실행: Supabase SQL Editor 에서 붙여넣어 실행
--
-- 전제:
--   - 랜딩 가입폼은 anon 키로 subscribers INSERT (is_active=true, plan='basic')
--   - 어드민은 Supabase Auth 로그인 후 authenticated 권한으로 동작
--   - Python 백엔드(수집·발송·대시보드) 는 service_role 키 사용 → RLS 우회

-- ───── subscribers ─────
ALTER TABLE subscribers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_signup" ON subscribers;
CREATE POLICY "anon_signup" ON subscribers
  FOR INSERT TO anon
  WITH CHECK (is_active = true AND plan = 'basic' AND stripe_customer_id IS NULL);

DROP POLICY IF EXISTS "admin_all" ON subscribers;
CREATE POLICY "admin_all" ON subscribers
  FOR ALL TO authenticated
  USING (true) WITH CHECK (true);

-- ───── weekly_reports ─────
ALTER TABLE weekly_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "admin_read" ON weekly_reports;
CREATE POLICY "admin_read" ON weekly_reports
  FOR SELECT TO authenticated USING (true);

-- ───── send_logs ─────
ALTER TABLE send_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "admin_read" ON send_logs;
CREATE POLICY "admin_read" ON send_logs
  FOR SELECT TO authenticated USING (true);

-- ───── collection_logs ─────
ALTER TABLE collection_logs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "admin_read" ON collection_logs;
CREATE POLICY "admin_read" ON collection_logs
  FOR SELECT TO authenticated USING (true);
