-- Migration: 001_add_unique_constraints
-- Description: assembly_pagesテーブルにUNIQUE制約を追加
-- Date: 2024-12-10
--
-- 注意: 既存のDBに対して実行するマイグレーションSQL
-- 新規DBの場合はschema.sqlで自動的に適用される

-- 1. image_urlのNOT NULL制約を削除（事前にページ枠を作成するため）
ALTER TABLE assembly_pages ALTER COLUMN image_url DROP NOT NULL;

-- 2. product_id + page_number の組み合わせにUNIQUE制約を追加
-- 同一商品内でページ番号の重複を防ぐ
ALTER TABLE assembly_pages
ADD CONSTRAINT assembly_pages_product_page_unique
UNIQUE (product_id, page_number);
