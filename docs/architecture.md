# システムアーキテクチャ設計書

## 1. システム概要
PBAP (PANZER BLOCKS Assist Parts) は、ユーザーが不足部品を申請し、管理者がそれを処理するためのWebアプリケーションです。
**ユーザー向けシステム**と**管理者向けシステム**を分離し、それぞれの用途に最適な技術スタックを採用します。

## 2. 技術スタック

### 2.1 ユーザー向けシステム (Public)
*   **目的**: 一般ユーザーによる不足部品申請。
*   **フレームワーク**: Next.js (App Router)
*   **言語**: TypeScript
*   **スタイリング**: Tailwind CSS
*   **インフラ**: Vercel (推奨) または Docker Container

### 2.2 管理者向けシステム (Internal)
*   **目的**: 申請タスク管理、発送処理、**商品・画像データの登録（画像処理含む）**。
*   **フレームワーク**: Streamlit (または FastAPI + Simple UI)
*   **言語**: Python
*   **ライブラリ**: OpenCV, YOLOv8 (画像処理), Supabase-py
*   **インフラ**: Docker Container (社内サーバー/クラウド)

### 2.3 共通バックエンド (BaaS)
*   **プラットフォーム**: Supabase
*   **データベース**: PostgreSQL
*   **ストレージ**: Supabase Storage (WebP画像)
*   **認証**:
    *   ユーザー側: 認証不要
    *   管理者側: 簡易認証 (環境変数/Basic認証) または Streamlit の認証機能

## 3. システム構成図

```mermaid
graph TD
    subgraph "User System (Public)"
        UserBrowser[ユーザーブラウザ] -->|HTTPS| NextApp[Next.js App]
    end

    subgraph "Admin System (Internal)"
        AdminBrowser[管理者ブラウザ] -->|HTTPS| PythonApp[Python App (Streamlit)]
        PythonApp -- 画像処理 --> OpenCV[OpenCV / YOLO]
    end

    subgraph "Shared Backend (Supabase)"
        NextApp -->|Read/Write| SupabaseDB[(PostgreSQL)]
        NextApp -->|Read| SupabaseStorage[Storage]
        
        PythonApp -->|Read/Write| SupabaseDB
        PythonApp -->|Read/Write| SupabaseStorage
    end
```

## 4. 非機能要件への対応

### 4.1 セキュリティ
*   **通信の暗号化**: 全通信をHTTPS化。
*   **管理者認証**: Pythonアプリ側で環境変数等を用いたアクセス制限を実施。
*   **データ保護**: Supabase RLS (Row Level Security) を設定し、不正な書き込みを防止（ユーザーは申請データのINSERTのみ許可など）。

### 4.2 パフォーマンス
*   **画像最適化**: ユーザー側は `next/image` で最適化配信。管理者側はPythonでアップロード時にWebP変換・リサイズを行う。
*   **処理負荷分散**: 画像処理という重い処理を管理者用Pythonサーバーに寄せることで、ユーザー用Next.jsサーバーの軽快さを維持。

### 4.3 可用性・保守性
*   **疎結合**: フロントエンド分離により、片方の改修が他方に影響しない。
*   **ログ**: 各アプリケーションのログに加え、管理者の操作ログ（ログイン、画像登録等）をテキストログとして記録。
