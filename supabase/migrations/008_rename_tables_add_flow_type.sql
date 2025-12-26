-- Migration: テーブルリネームとflow_type追加
-- 実行前に既存データをバックアップしてください（必要な場合）

-- 1. 既存のRLSポリシーを削除
DROP POLICY IF EXISTS "Public read access for task_details" ON task_details;
DROP POLICY IF EXISTS "Enable insert for anon" ON task_details;
DROP POLICY IF EXISTS "Enable update for anon" ON task_details;
DROP POLICY IF EXISTS "Enable delete for anon" ON task_details;

-- 2. task_details を task_part_requests にリネーム
ALTER TABLE IF EXISTS task_details RENAME TO task_part_requests;

-- 3. tasksテーブルに flow_type カラムを追加
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS flow_type VARCHAR(20) NOT NULL DEFAULT 'normal';

-- 4. task_photo_requests テーブルを新規作成
CREATE TABLE IF NOT EXISTS task_photo_requests (
    id VARCHAR(50) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    task_id VARCHAR(50) REFERENCES tasks(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,              -- 印付き画像のURL（Supabase Storage）
    display_order INT NOT NULL DEFAULT 1, -- 表示順
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. RLSを有効化
ALTER TABLE task_part_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_photo_requests ENABLE ROW LEVEL SECURITY;

-- 6. task_part_requests のRLSポリシー
CREATE POLICY "Public read access for task_part_requests" ON task_part_requests FOR SELECT USING (true);
CREATE POLICY "Enable insert for anon" ON task_part_requests FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON task_part_requests FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON task_part_requests FOR DELETE USING (true);

-- 7. task_photo_requests のRLSポリシー
CREATE POLICY "Public read access for task_photo_requests" ON task_photo_requests FOR SELECT USING (true);
CREATE POLICY "Enable insert for anon" ON task_photo_requests FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON task_photo_requests FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON task_photo_requests FOR DELETE USING (true);

-- 完了メッセージ
SELECT 'Migration completed successfully' as status;
