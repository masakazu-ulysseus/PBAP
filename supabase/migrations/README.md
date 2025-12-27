# Database Migrations

このディレクトリには、既存のデータベースに対するマイグレーションSQLを管理しています。

## ファイル命名規則

```
{番号}_{説明}.sql
例: 001_add_unique_constraints.sql
```

## 実行方法

1. Supabaseダッシュボードにログイン
2. **SQL Editor** を開く
3. 該当のマイグレーションファイルの内容をコピー＆ペースト
4. **Run** をクリック

## マイグレーション一覧

| ファイル | 説明 | 適用日 |
|---------|------|--------|
| 001_add_unique_constraints.sql | assembly_pagesにUNIQUE制約追加 | 2024-12-10 |
| 002_assembly_images_nullable_unique.sql | assembly_imagesにNULL許容とUNIQUE制約追加 | 2024-12-10 |
| 003_add_display_order_to_assembly_image_parts.sql | assembly_image_partsにdisplay_order追加、part_idをNULL許可に変更 | 2024-12-11 |
| 004_add_product_image_url.sql | productsにimage_url追加 | 2024-12-16 |
| 005_add_region_coordinates_to_assembly_images.sql | assembly_imagesに座標情報(region_x/y/width/height)追加 | 2024-12-16 |
| 006_add_email_tracking_and_tasks_rls.sql | tasksにメール送信追跡カラム追加、RLSポリシー追加 | 2024-12-18 |
| 007_add_application_number.sql | tasksにapplication_number(申請番号)追加 | 2024-12-19 |
| 008_rename_tables_add_flow_type.sql | テーブル名変更、flow_type追加 | 2024-12-25 |
| 009_add_user_memo.sql | tasksにuser_memo追加 | 2024-12-25 |
| 010_split_address_fields.sql | 住所フィールド分割(prefecture/city/town/address_detail/building_name) | 2024-12-26 |
| 011_add_other_product_name.sql | tasksにother_product_name追加（その他フロー用） | 2024-12-27 |
| 012_rename_parts_size_to_parts_code.sql | partsのsizeカラムをparts_codeにリネーム | 2024-12-27 |

## 注意事項

- 新規DBの場合は `schema.sql` で自動的に制約が適用されます
- マイグレーションは既存のDBに対してのみ実行してください
- 実行前に必ずバックアップを取得することを推奨します
