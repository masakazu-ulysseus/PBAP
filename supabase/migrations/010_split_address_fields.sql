-- 住所フィールドを分割するマイグレーション
-- 郵便番号から住所自動入力機能のため

-- 1. 新しいカラムを追加
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS prefecture VARCHAR(10);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS town VARCHAR(100);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS address_detail VARCHAR(255);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS building_name VARCHAR(255);

-- 2. 既存データを移行（既存のaddressカラムの値をaddress_detailに移動）
UPDATE tasks
SET
    prefecture = '',
    city = '',
    town = '',
    address_detail = address,
    building_name = ''
WHERE prefecture IS NULL;

-- 3. NOT NULL制約を追加（既存データ移行後）
ALTER TABLE tasks ALTER COLUMN prefecture SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN city SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN address_detail SET NOT NULL;

-- 4. 旧addressカラムを削除
ALTER TABLE tasks DROP COLUMN IF EXISTS address;

-- 5. コメント追加
COMMENT ON COLUMN tasks.prefecture IS '都道府県（自動入力）';
COMMENT ON COLUMN tasks.city IS '市区町村（自動入力）';
COMMENT ON COLUMN tasks.town IS '町域（自動入力）';
COMMENT ON COLUMN tasks.address_detail IS '番地（手動入力・必須）';
COMMENT ON COLUMN tasks.building_name IS '建物名（手動入力・任意）';
