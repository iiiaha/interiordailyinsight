-- Security Advisor 경고 해소
-- 실행: Supabase SQL Editor 에서 붙여넣어 실행
--
-- 1. update_updated_at() 함수 search_path 고정 (함수 하이재킹 방지)
-- 2. admin_* 정책을 관리자 이메일로 좁힘 (공개 가입 시 보안 마진)
--
-- 관리자 이메일: iiiaha@naver.com
-- 관리자 계정이 바뀌면 이 파일의 이메일을 수정하고 재실행.

-- ───── 1. Function search_path ─────
ALTER FUNCTION public.update_updated_at() SET search_path = '';

-- ───── 2. subscribers 정책 좁히기 ─────
DROP POLICY IF EXISTS "admin_all" ON subscribers;
CREATE POLICY "admin_all" ON subscribers
  FOR ALL TO authenticated
  USING ((auth.jwt() ->> 'email') = 'iiiaha@naver.com')
  WITH CHECK ((auth.jwt() ->> 'email') = 'iiiaha@naver.com');

-- ───── weekly_reports ─────
DROP POLICY IF EXISTS "admin_read" ON weekly_reports;
CREATE POLICY "admin_read" ON weekly_reports
  FOR SELECT TO authenticated
  USING ((auth.jwt() ->> 'email') = 'iiiaha@naver.com');

-- ───── send_logs ─────
DROP POLICY IF EXISTS "admin_read" ON send_logs;
CREATE POLICY "admin_read" ON send_logs
  FOR SELECT TO authenticated
  USING ((auth.jwt() ->> 'email') = 'iiiaha@naver.com');

-- ───── collection_logs ─────
DROP POLICY IF EXISTS "admin_read" ON collection_logs;
CREATE POLICY "admin_read" ON collection_logs
  FOR SELECT TO authenticated
  USING ((auth.jwt() ->> 'email') = 'iiiaha@naver.com');
