-- Migration: 002_assembly_images_nullable_unique
-- Description: assembly_imagesテーブルにNULL許容とUNIQUE制約を追加
-- Date: 2024-12-10
--
-- 注意: 既存のDBに対して実行するマイグレーションSQL
-- 新規DBの場合はschema.sqlで自動的に適用される

-- 1. image_urlのNOT NULL制約を削除（事前に組立番号枠を作成するため）
ALTER TABLE assembly_images ALTER COLUMN image_url DROP NOT NULL;

-- 2. page_id + assembly_number の組み合わせにUNIQUE制約を追加
-- 同一ページ内で組立番号の重複を防ぐ
ALTER TABLE assembly_images
ADD CONSTRAINT assembly_images_page_number_unique
UNIQUE (page_id, assembly_number);
