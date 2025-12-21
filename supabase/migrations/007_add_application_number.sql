-- 申請番号用のシーケンスを作成（10000から開始）
CREATE SEQUENCE IF NOT EXISTS task_application_number_seq
    START WITH 10000
    INCREMENT BY 1
    NO MAXVALUE
    NO CYCLE;

-- tasksテーブルに申請番号カラムを追加
ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS application_number INT UNIQUE;

-- 既存レコードに申請番号を付与（もしあれば）
UPDATE tasks
SET application_number = nextval('task_application_number_seq')
WHERE application_number IS NULL;

-- 今後の新規レコードにはデフォルト値としてシーケンスを使用
ALTER TABLE tasks
ALTER COLUMN application_number SET DEFAULT nextval('task_application_number_seq');

-- application_numberをNOT NULLに変更（既存データに値が入った後）
-- 注意: 既存データがない場合のみ実行可能
-- ALTER TABLE tasks ALTER COLUMN application_number SET NOT NULL;

-- インデックスを作成（検索パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_tasks_application_number ON tasks(application_number);

-- コメント追加
COMMENT ON COLUMN tasks.application_number IS '申請番号（10000から始まる連番）';
