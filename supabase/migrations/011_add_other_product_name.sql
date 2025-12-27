-- Migration: 011_add_other_product_name
-- Description: その他フローでユーザーが入力した商品名を保存するカラムを追加
-- Date: 2024-12-27

-- tasksテーブルにother_product_nameカラムを追加
-- 通常フロー: NULL
-- その他フロー: ユーザーが入力した商品名
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS other_product_name VARCHAR(100);

COMMENT ON COLUMN tasks.other_product_name IS 'その他フローでユーザーが入力した商品名（通常フローではNULL）';
