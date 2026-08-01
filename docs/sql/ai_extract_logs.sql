-- ============================================================
-- 钛星 · ai_extract_logs — AI 提取历史记录表（管理后台专用）
-- 说明：
--   1. v3 设计方案中唯一新增的后台专用表，现有业务表结构一律不动。
--   2. 后端代码【不会】强制建表；表不存在时读写均自动容错（不影响主流程）。
--   3. 请在 Supabase SQL Editor 中执行本文件（幂等，可重复执行）。
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_extract_logs (
  id         BIGSERIAL PRIMARY KEY,
  category   TEXT,
  limit      INT,
  total      INT,
  inserted   INT,
  failed     INT,
  status     TEXT,
  message    TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 历史列表按时间倒序查询，加快后台展示
CREATE INDEX IF NOT EXISTS idx_ai_extract_logs_created_at
  ON ai_extract_logs (created_at DESC);