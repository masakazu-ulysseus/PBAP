-- Migration: Add display_order column to assembly_image_parts table
-- Date: 2024-12-11
-- Description: 部品枠を事前に作成し、後から画像を割り当てる機能のためのスキーマ変更

-- 1. display_order カラムを追加
ALTER TABLE assembly_image_parts
ADD COLUMN IF NOT EXISTS display_order INT DEFAULT 1;

-- 2. 既存レコードにdisplay_orderを設定（assembly_image_id毎に連番）
WITH numbered AS (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY assembly_image_id ORDER BY created_at, id) as rn
    FROM assembly_image_parts
)
UPDATE assembly_image_parts
SET display_order = numbered.rn
FROM numbered
WHERE assembly_image_parts.id = numbered.id;

-- 3. display_orderにNOT NULL制約を追加
ALTER TABLE assembly_image_parts
ALTER COLUMN display_order SET NOT NULL;

-- 4. part_id の外部キー制約を変更（ON DELETE CASCADEからON DELETE SET NULLへ）
-- 注意: 既存の外部キー制約名を確認してから実行してください
-- ALTER TABLE assembly_image_parts DROP CONSTRAINT IF EXISTS assembly_image_parts_part_id_fkey;
-- ALTER TABLE assembly_image_parts
-- ADD CONSTRAINT assembly_image_parts_part_id_fkey
-- FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE SET NULL;

-- 確認用クエリ
-- SELECT * FROM assembly_image_parts ORDER BY assembly_image_id, display_order;
