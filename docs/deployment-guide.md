# PBAP デプロイガイド

本番環境へのデプロイ手順書です。

## 概要

| コンポーネント | デプロイ先 | URL |
|---------------|-----------|-----|
| Supabase | Supabase Cloud | (Project URL) |
| admin-tool | 社内サーバー (Docker) | http://(サーバーIP):8501 |
| user-app | Vercel | https://pbap.panzer-blocks.com |

## デプロイ順序

```
1. Supabase 初期設定
   ↓
2. admin-tool デプロイ（社内サーバー）
   ↓
3. user-app デプロイ（Vercel）
```

---

## 1. Supabase 初期設定

### 1.1 アカウント・プロジェクト作成

1. [Supabase](https://supabase.com/) にアクセス
2. アカウント作成（GitHub連携推奨）
3. 「New Project」をクリック
4. プロジェクト情報を入力:
   - **Name**: `pbap-production`（任意）
   - **Database Password**: 強力なパスワードを設定（控えておく）
   - **Region**: `Northeast Asia (Tokyo)` 推奨
5. 「Create new project」をクリック

### 1.2 データベース作成（schema.sql実行）

1. Supabaseダッシュボード → **SQL Editor**
2. 「New query」をクリック
3. `supabase/schema.sql` の内容をコピー＆ペースト
4. 「Run」をクリック
5. エラーがないことを確認

### 1.2.1 開発環境との照合確認（推奨）

本番環境のデータベース構造が開発環境と一致していることを確認します。

1. **本番環境のテーブル構造をエクスポート**

   Supabaseダッシュボード → **SQL Editor** で以下を実行:

   ```sql
   SELECT
     table_name,
     column_name,
     data_type,
     is_nullable
   FROM information_schema.columns
   WHERE table_schema = 'public'
   ORDER BY table_name, ordinal_position;
   ```

2. **結果をCSVでダウンロード**
   - 結果パネルの「↓」ボタン →「Download as CSV」
   - ファイル名: `PBAP-Prod_Supabase.csv` 等

3. **開発環境と比較**
   - 開発環境でも同様のクエリを実行しCSVをダウンロード
   - 両者のCSVを比較（テーブル数、カラム名、データ型、NULL許容）

4. **期待される結果（8テーブル）**
   - assembly_image_parts
   - assembly_images
   - assembly_pages
   - parts
   - products
   - task_part_requests
   - task_photo_requests
   - tasks

5. **差分がある場合**
   - schema.sqlを修正
   - 既存テーブルを削除（`DROP TABLE IF EXISTS xxx CASCADE;`）
   - schema.sqlを再実行
   - 再度照合確認

### 1.3 Storageバケット確認

schema.sql実行で自動作成されますが、念のため確認:

1. Supabaseダッシュボード → **Storage**
2. `product-images` バケットが存在することを確認
3. 存在しない場合は手動作成:
   - 「New bucket」→ Name: `product-images`、Public bucket: ON

### 1.4 アクセストークン取得

1. Supabaseダッシュボード → **Settings** → **API**
2. 以下の値を控える:

| 項目 | 用途 |
|------|------|
| **Project URL** | SUPABASE_URL / NEXT_PUBLIC_SUPABASE_URL |
| **anon public** | SUPABASE_KEY / NEXT_PUBLIC_SUPABASE_ANON_KEY |
| **service_role** (secret) | 将来の管理用（現時点では不使用） |

---

## 2. admin-tool デプロイ（社内サーバー）

### 前提条件

- 社内サーバーにDockerがインストール済み
- Git がインストール済み
- ポート8501が開放されている

### 2.1 リポジトリ取得

```bash
# サーバーにSSH接続後
cd /opt  # または任意のディレクトリ
git clone https://github.com/(your-org)/PBAP.git
git clone https://github.com/masakazu-ulysseus/PBAP.git
cd PBAP/apps/admin-tool
```

### 2.2 環境変数設定

```bash
cp .env.example .env  # または新規作成
nano .env
```

`.env` ファイル内容:

```env
# Supabase設定（必須）
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# SMTP設定（メール送信用・任意）
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
SMTP_FROM=noreply@example.com
```

### 2.3 Dockerイメージビルド・起動

```bash
cd apps/admin-tool

# ログディレクトリ作成（初回のみ）
sudo mkdir -p logs
sudo chown -R 1000:1000 logs

# ビルド
sudo docker compose build

# 起動（バックグラウンド）
sudo docker compose up -d

# ログ確認
sudo docker compose logs -f
```

### 2.4 疎通確認

1. ブラウザで `http://(サーバーIP):8501` にアクセス
2. admin-toolのダッシュボードが表示されることを確認
3. 商品登録ページで新規商品を登録してみる
4. Supabaseダッシュボード → Table Editor で登録されたデータを確認

### 2.5 運用コマンド

```bash
# 停止
sudo docker compose down

# 再起動
sudo docker compose restart

# ログ確認
sudo docker compose logs -f admin-tool

# 更新（git pull後）
cd /opt/PBAP
git pull
cd apps/admin-tool
sudo docker compose build
sudo docker compose up -d
```

---

## 3. user-app デプロイ（Vercel）

### 3.1 Vercelアカウント・プロジェクト作成

1. [Vercel](https://vercel.com/) にアクセス
2. GitHubアカウントでログイン
3. 「Add New...」→「Project」
4. GitHubリポジトリ `PBAP` をインポート
5. プロジェクト設定:
   - **Framework Preset**: Next.js（自動検出）
   - **Root Directory**: `apps/user-app`
   - **Build Command**: `npm run build`（デフォルト）
   - **Output Directory**: `.next`（デフォルト）

### 3.2 環境変数設定

Vercelダッシュボード → Settings → Environment Variables

| 変数名 | 値 | 環境 |
|--------|-----|------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase Project URL | Production, Preview, Development |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon public key | Production, Preview, Development |
| `NEXT_PUBLIC_SITE_URL` | `https://pbap.panzer-blocks.com` | Production |
| `SMTP_HOST` | SMTPサーバーホスト | Production |
| `SMTP_PORT` | `587` | Production |
| `SMTP_USER` | SMTPユーザー | Production |
| `SMTP_PASSWORD` | SMTPパスワード | Production |
| `SMTP_FROM` | 送信元メールアドレス（任意） | Production |
| `SMTP_SECURE` | `false` | Production |

### 3.3 デプロイ実行

1. 環境変数設定後、「Deploy」をクリック
2. ビルドログを確認（エラーがないこと）
3. デプロイ完了後、プレビューURLで動作確認

### 3.4 カスタムドメイン設定

1. Vercelダッシュボード → Settings → Domains
2. 「Add」をクリック
3. `pbap.panzer-blocks.com` を入力
4. DNSレコード設定:

**方法A: CNAMEレコード（推奨）**

ドメイン管理画面（お名前.com、Cloudflare等）で以下を設定:

| タイプ | ホスト | 値 |
|--------|--------|-----|
| CNAME | pbap | cname.vercel-dns.com |

**方法B: Aレコード**

| タイプ | ホスト | 値 |
|--------|--------|-----|
| A | pbap | 76.76.21.21 |

5. DNS反映を待つ（最大48時間、通常は数分〜数時間）
6. Vercelで「Verify」をクリック
7. SSL証明書が自動発行される

### 3.5 疎通確認

1. `https://pbap.panzer-blocks.com` にアクセス
2. トップページが表示されることを確認
3. 「申請する」ボタンから申請フローをテスト
4. メール受信を確認（SMTP設定済みの場合）

---

## 環境変数一覧

### admin-tool

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `SUPABASE_URL` | ◯ | Supabase Project URL |
| `SUPABASE_KEY` | ◯ | Supabase anon public key |
| `SMTP_HOST` | - | SMTPサーバーホスト |
| `SMTP_PORT` | - | SMTPポート（デフォルト: 587） |
| `SMTP_USER` | - | SMTP認証ユーザー |
| `SMTP_PASSWORD` | - | SMTP認証パスワード |
| `SMTP_FROM` | - | 送信元メールアドレス |

### user-app

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `NEXT_PUBLIC_SUPABASE_URL` | ◯ | Supabase Project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ◯ | Supabase anon public key |
| `NEXT_PUBLIC_SITE_URL` | ◯ | サイトURL（PDF生成API用） |
| `SMTP_HOST` | - | SMTPサーバーホスト |
| `SMTP_PORT` | - | SMTPポート（デフォルト: 587） |
| `SMTP_USER` | - | SMTP認証ユーザー |
| `SMTP_PASSWORD` | - | SMTP認証パスワード |
| `SMTP_FROM` | - | 送信元メールアドレス |
| `SMTP_SECURE` | - | SSL使用（465の場合true、587の場合false） |

---

## トラブルシューティング

### admin-tool が起動しない

```bash
# ログを確認
docker compose logs admin-tool

# よくある原因
# - .envファイルが存在しない
# - SUPABASE_URL/KEYが未設定
# - ポート8501が既に使用中
```

### user-app ビルドエラー

```bash
# よくある原因
# - 環境変数が未設定
# - Root Directoryが正しく設定されていない（apps/user-app）
```

### メールが送信されない

1. SMTP設定が正しいか確認
2. Vercelログで `SMTP not configured, skipping email` が出ていないか確認
3. 送信元ドメインのSPF/DKIM設定を確認

### Supabase接続エラー

1. SUPABASE_URL/KEYが正しいか確認
2. RLSポリシーが正しく設定されているか確認（schema.sql再実行）
3. Supabaseダッシュボードでプロジェクトがアクティブか確認

---

## 更新手順

### admin-tool

```bash
cd /opt/PBAP
git pull
cd apps/admin-tool
docker compose build
docker compose up -d
```

### user-app

GitHubにpushすると自動デプロイされます:

```bash
git add .
git commit -m "Update"
git push origin main
```

Vercelダッシュボードでデプロイ状況を確認できます。
