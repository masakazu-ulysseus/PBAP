-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Products Table
CREATE TABLE products (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    series_name VARCHAR(100) NOT NULL,
    country VARCHAR(100),
    release_date DATE,
    status VARCHAR(20) NOT NULL,
    image_url TEXT,  -- 製品画像のURL（Supabase Storageに保存）
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Assembly Pages Table
CREATE TABLE assembly_pages (
    id VARCHAR(50) PRIMARY KEY,
    product_id VARCHAR(50) REFERENCES products(id) ON DELETE CASCADE,
    page_number INT NOT NULL,
    image_url TEXT,  -- NULLable: 事前にページ枠を作成し、後から画像を登録するため
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (product_id, page_number)  -- 同一商品内でページ番号は一意
);

-- 3. Assembly Images Table
CREATE TABLE assembly_images (
    id VARCHAR(50) PRIMARY KEY,
    page_id VARCHAR(50) REFERENCES assembly_pages(id) ON DELETE CASCADE,
    assembly_number VARCHAR(20) NOT NULL,
    display_order INT NOT NULL,
    image_url TEXT,  -- NULLable: 事前に組立番号枠を作成し、後から画像を登録するため
    region_x INT,           -- 組立ページ画像内での左上X座標（ピクセル）
    region_y INT,           -- 組立ページ画像内での左上Y座標（ピクセル）
    region_width INT,       -- 領域の幅（ピクセル）
    region_height INT,      -- 領域の高さ（ピクセル）
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (page_id, assembly_number)  -- 同一ページ内で組立番号は一意
);

-- 4. Parts Table
CREATE TABLE parts (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100), -- Nullable
    parts_url TEXT,
    color VARCHAR(50),
    size VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Assembly Image Parts (Intermediate Table)
-- 部品枠を事前に作成し、後から部品画像を割り当てるため、part_idはNULL許可
CREATE TABLE assembly_image_parts (
    id VARCHAR(50) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    assembly_image_id VARCHAR(50) REFERENCES assembly_images(id) ON DELETE CASCADE,
    part_id VARCHAR(50) REFERENCES parts(id) ON DELETE SET NULL,  -- NULL許可、削除時はNULLに
    quantity INT DEFAULT 1,
    display_order INT NOT NULL DEFAULT 1,  -- 部品の表示順（1から開始）
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Tasks Table
-- 申請番号用のシーケンス（10000から開始）
CREATE SEQUENCE IF NOT EXISTS task_application_number_seq
    START WITH 10000
    INCREMENT BY 1
    NO MAXVALUE
    NO CYCLE;

CREATE TABLE tasks (
    id VARCHAR(50) PRIMARY KEY,
    application_number INT UNIQUE DEFAULT nextval('task_application_number_seq'),  -- 申請番号（10000から始まる連番）
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    zip_code VARCHAR(10) NOT NULL,
    address TEXT NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    recipient_name VARCHAR(100) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    purchase_store VARCHAR(255) NOT NULL,
    purchase_date DATE NOT NULL,
    warranty_code VARCHAR(50) NOT NULL,
    admin_memo TEXT,
    shipment_image_url TEXT,
    email_sent_at TIMESTAMPTZ,        -- メール送信日時
    email_error TEXT,                  -- メール送信エラーメッセージ
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 申請番号の検索用インデックス
CREATE INDEX IF NOT EXISTS idx_tasks_application_number ON tasks(application_number);

-- 7. Task Details Table
CREATE TABLE task_details (
    id VARCHAR(50) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    task_id VARCHAR(50) REFERENCES tasks(id) ON DELETE CASCADE,
    part_id VARCHAR(50) REFERENCES parts(id) ON DELETE CASCADE,
    assembly_image_id VARCHAR(50) REFERENCES assembly_images(id) ON DELETE SET NULL,
    quantity INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policies (Placeholder - Allow all for now, refine later)
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE assembly_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE assembly_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE assembly_image_parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_details ENABLE ROW LEVEL SECURITY;

-- Public read access for products and related tables
CREATE POLICY "Public read access for products" ON products FOR SELECT USING (true);
CREATE POLICY "Public read access for assembly_pages" ON assembly_pages FOR SELECT USING (true);
CREATE POLICY "Public read access for assembly_images" ON assembly_images FOR SELECT USING (true);
CREATE POLICY "Public read access for parts" ON parts FOR SELECT USING (true);
CREATE POLICY "Public read access for assembly_image_parts" ON assembly_image_parts FOR SELECT USING (true);

-- Admin write access (simplified for now, assumes service role or authenticated admin)
-- Ideally, we should check for admin role, but for MVP/Internal tool, we might rely on Service Role Key for writing.

-- For Admin Tool using Anon Key, we need to allow Write operations.
-- WARNING: This allows ANYONE with the Anon Key to modify data. secure this later with Auth.
CREATE POLICY "Enable insert for anon" ON products FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON products FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON products FOR DELETE USING (true);

CREATE POLICY "Enable insert for anon" ON assembly_pages FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON assembly_pages FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON assembly_pages FOR DELETE USING (true);

CREATE POLICY "Enable insert for anon" ON assembly_images FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON assembly_images FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON assembly_images FOR DELETE USING (true);

CREATE POLICY "Enable insert for anon" ON parts FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON parts FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON parts FOR DELETE USING (true);

CREATE POLICY "Enable insert for anon" ON assembly_image_parts FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON assembly_image_parts FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON assembly_image_parts FOR DELETE USING (true);

CREATE POLICY "Public read access for tasks" ON tasks FOR SELECT USING (true);
CREATE POLICY "Enable insert for anon" ON tasks FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON tasks FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON tasks FOR DELETE USING (true);

CREATE POLICY "Public read access for task_details" ON task_details FOR SELECT USING (true);
CREATE POLICY "Enable insert for anon" ON task_details FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for anon" ON task_details FOR UPDATE USING (true);
CREATE POLICY "Enable delete for anon" ON task_details FOR DELETE USING (true);

-- Storage Bucket Setup
INSERT INTO storage.buckets (id, name, public) 
VALUES ('product-images', 'product-images', true)
ON CONFLICT (id) DO NOTHING;

-- Storage Policies
CREATE POLICY "Public Access" ON storage.objects FOR SELECT USING ( bucket_id = 'product-images' );
CREATE POLICY "Public Insert" ON storage.objects FOR INSERT WITH CHECK ( bucket_id = 'product-images' );
CREATE POLICY "Public Update" ON storage.objects FOR UPDATE USING ( bucket_id = 'product-images' );
