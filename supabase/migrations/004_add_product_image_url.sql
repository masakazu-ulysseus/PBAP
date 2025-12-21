-- Migration: 004_add_product_image_url.sql
-- Date: 2025-12-16
-- Description: Add image_url column to products table for product photos

-- Add image_url column to products table
ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url TEXT;

-- Comment explaining the column
COMMENT ON COLUMN products.image_url IS '製品画像のURL（Supabase Storageに保存）';
