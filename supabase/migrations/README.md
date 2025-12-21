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
| 001_add_unique_constraints.sql | assembly_pagesにUNIQUE制約追加 | - |
| 002_assembly_images_nullable_unique.sql | assembly_imagesにNULL許容とUNIQUE制約追加 | - |
| 003_add_display_order_to_assembly_image_parts.sql | assembly_image_partsにdisplay_order追加、part_idをNULL許可に変更 | - |

## 注意事項

- 新規DBの場合は `schema.sql` で自動的に制約が適用されます
- マイグレーションは既存のDBに対してのみ実行してください
- 実行前に必ずバックアップを取得することを推奨します
