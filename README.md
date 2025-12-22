# PBAP (PANZER BLOCKS Assist Parts)

PANZER BLOCKS製品の部品請求を管理するWebアプリケーションシステムです。

## 概要

PBAPは2つのアプリケーションで構成されています：

| アプリケーション | 技術スタック | 説明 |
|-----------------|-------------|------|
| **Admin Tool** | Python / Streamlit | 商品・画像登録、タスク管理用の内部管理ツール |
| **User App** | Next.js / TypeScript | ユーザー向け部品請求フォーム |

## システム構成図

```
┌─────────────────┐     ┌─────────────────┐
│   User App      │     │   Admin Tool    │
│  (Next.js)      │     │  (Streamlit)    │
│  Port: 3000     │     │  Port: 8501     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │   Supabase  │
              │ ┌─────────┐ │
              │ │PostgreSQL│ │
              │ └─────────┘ │
              │ ┌─────────┐ │
              │ │ Storage │ │
              │ └─────────┘ │
              └─────────────┘
```

## データモデル

```
Products → AssemblyPages → AssemblyImages → Parts
                                    ↓
                           AssemblyImageParts (junction)

Tasks → TaskDetails → Parts
```

- **Products**: 商品マスタ（名前、シリーズ、国）
- **AssemblyPages**: 組立説明書ページ（大きな画像）
- **AssemblyImages**: 組立番号領域（中サイズ画像）+ 座標情報
- **Parts**: 個別部品画像（小さな画像）
- **Tasks**: ユーザーからの部品請求
- **TaskDetails**: 請求ごとの部品詳細

## セットアップ

### 前提条件

- Python 3.10+
- Node.js 18+
- Supabaseアカウント

### Admin Tool

```bash
cd apps/admin-tool

# 仮想環境の作成・有効化
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .envを編集してSupabaseの認証情報を設定

# 起動
streamlit run src/main.py
```

### User App

```bash
cd apps/user-app

# 依存関係のインストール
npm install

# 環境変数の設定
cp .env.example .env.local
# .env.localを編集してSupabaseの認証情報を設定

# 開発サーバー起動
npm run dev
```

### データベース

Supabaseダッシュボードで `supabase/schema.sql` を実行してスキーマを適用します。

## 環境変数

### Admin Tool (`apps/admin-tool/.env`)

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

### User App (`apps/user-app/.env.local`)

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
RESEND_API_KEY=your_resend_api_key
```

## プロジェクト構造

```
PBAP/
├── apps/
│   ├── admin-tool/          # 管理ツール (Python/Streamlit)
│   │   ├── src/
│   │   │   ├── main.py      # エントリーポイント
│   │   │   ├── pages/       # 各ページコンポーネント
│   │   │   ├── utils/       # ユーティリティ関数
│   │   │   └── tests/       # テスト
│   │   └── requirements.txt
│   │
│   └── user-app/            # ユーザーアプリ (Next.js)
│       ├── src/
│       │   ├── app/         # App Router ページ
│       │   ├── components/  # UIコンポーネント
│       │   ├── lib/         # ユーティリティ
│       │   └── types/       # 型定義
│       └── package.json
│
├── supabase/
│   └── schema.sql           # データベーススキーマ
│
├── poc/                     # 画像処理アルゴリズムの実験
│
└── docs/                    # ドキュメント
```

## 主要機能

### Admin Tool

- **商品管理**: 商品の登録・編集・削除
- **組立ページ管理**: 組立説明書ページの画像登録
- **組立番号検出**: 自動検出または手動切り出し（座標情報付き）
- **部品抽出**: OpenCVによる自動部品画像抽出
- **タスク管理**: ユーザーからの部品請求の処理

### User App

- **商品選択**: 部品請求する商品を選択
- **部品選択**: 組立画像から必要な部品を選択（座標ベースのオーバーレイ表示）
- **購入情報入力**: 購入場所・日時の入力
- **配送情報入力**: 配送先住所の入力
- **PDF生成**: 請求内容のPDF出力
- **メール送信**: 確認メールの自動送信

## 技術的特徴

### 画像処理パイプライン

1. **組立番号検出**: HSV色空間を使用した黒/赤テキストの識別
2. **部品抽出**:
   - 最大矩形フレームの検出
   - 超解像処理（2倍アップスケール）
   - シャープニング（アンシャープマスク）
   - ノイズ除去（メディアンフィルタ）
   - 輪郭検出（面積・アスペクト比フィルタリング）

### 画像最適化

- WebP形式に変換
- 最大2000pxにリサイズ
- Supabase Storageで公開配信

## 開発コマンド

### Admin Tool

```bash
# テスト実行
pytest src/tests/

# 特定のテストファイル
pytest src/tests/test_image_processing.py -v

# Lint
pyflakes src/
```

### User App

```bash
# Lint
npm run lint

# 型チェック
npm run type-check

# ビルド
npm run build
```

## ライセンス

Private - All rights reserved
