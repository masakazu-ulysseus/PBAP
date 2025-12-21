-- Migration: 005_add_region_coordinates_to_assembly_images.sql
-- Date: 2025-12-16
-- Description: Add region coordinates to assembly_images table for click-to-select functionality

-- Add region coordinate columns to assembly_images table
ALTER TABLE assembly_images ADD COLUMN IF NOT EXISTS region_x INT;
ALTER TABLE assembly_images ADD COLUMN IF NOT EXISTS region_y INT;
ALTER TABLE assembly_images ADD COLUMN IF NOT EXISTS region_width INT;
ALTER TABLE assembly_images ADD COLUMN IF NOT EXISTS region_height INT;

-- Comments explaining the columns
COMMENT ON COLUMN assembly_images.region_x IS '組立ページ画像内での左上X座標（ピクセル）';
COMMENT ON COLUMN assembly_images.region_y IS '組立ページ画像内での左上Y座標（ピクセル）';
COMMENT ON COLUMN assembly_images.region_width IS '領域の幅（ピクセル）';
COMMENT ON COLUMN assembly_images.region_height IS '領域の高さ（ピクセル）';
