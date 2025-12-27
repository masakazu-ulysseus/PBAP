-- Migration: 012_rename_parts_size_to_parts_code
-- Description: partsテーブルのsizeカラムをparts_codeにリネーム
-- Date: 2024-12-27

-- sizeカラムをparts_codeにリネーム
-- 将来的なパーツコード管理用
ALTER TABLE parts RENAME COLUMN size TO parts_code;

COMMENT ON COLUMN parts.parts_code IS 'パーツコード（将来的なコード管理用）';
