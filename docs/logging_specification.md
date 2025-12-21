# PBAP ログ仕様書

## 概要

PBAP（PANZER BLOCKS Assist Parts）アプリケーションのログ仕様について説明します。
ユーザー向けシステム（Next.js）と管理ツール（Python/Streamlit）で異なるロギングライブラリを使用しています。

---

# Part 1: 管理ツール (Python/Streamlit)

## 技術スタック

- **Loggerライブラリ**: Loguru
- **ログファイル**: ローテーション付きファイル出力
- **出力先**: `apps/admin-tool/logs/`

## ログファイル構成

| ファイル | レベル | 用途 |
|---------|-------|------|
| `operation.log` | INFO, SUCCESS, WARNING | 操作ログ（通常の操作記録） |
| `error.log` | ERROR以上 | エラーログ（スタックトレース付き） |

## ログローテーション設定

- **最大サイズ**: 5MB
- **保持世代数**: 3
- **圧縮**: ZIP形式
- **エンコーディング**: UTF-8

## ログフォーマット

### コンソール出力
```
2025-12-21 10:30:45 | INFO     | module:function:123 - ログメッセージ
```

### ファイル出力（operation.log）
```
2025-12-21 10:30:45 | INFO     | module:function:123 - ログメッセージ
```

### エラーログ（error.log）
```
2025-12-21 10:30:45 | ERROR    | module:function:123 - エラーメッセージ
Traceback (most recent call last):
  ...（スタックトレース）...
```

## 使用方法

```python
from utils.logger import logger

# 通常のログ
logger.info("商品登録: name=Tiger I, id=xxx")
logger.warning("画像サイズが大きすぎます: 5000x3000")

# エラーログ（例外情報付き）
try:
    # 処理
except Exception as e:
    logger.error(f"保存エラー: {e}")
```

## 主要ログイベント（管理ツール）

### 商品・画像登録

```python
logger.info(f"商品登録: name={product_name}, id={product_id}, pages={page_count}")
logger.info(f"ページ画像保存: page_id={page_id}")
logger.info(f"組立番号登録: assembly_number={num}, page_id={page_id}")
logger.info(f"部品画像保存: part_id={part_id}")
```

### 削除操作

```python
logger.info(f"商品削除: name={name}, id={id}, pages={deleted_pages}, parts={deleted_parts}")
logger.info(f"組立番号削除: id={assembly_id}")
logger.info(f"部品削除: id={part_id}")
```

### タスク管理

```python
logger.info(f"タスクステータス更新: ID={task_id}, status={new_status}")
logger.info(f"タスクメモ保存: ID={task_id}")
logger.info(f"発送部品画像アップロード: ID={task_id}")
logger.info(f"メール送信成功・タスク完了: ID={task_id}, email={email}")
logger.error(f"メール送信失敗: ID={task_id}, error={error}")
```

### エラー

```python
logger.error(f"商品登録エラー: {e}")
logger.error(f"画像処理エラー: {e}")
logger.error(f"Supabase接続エラー: {e}")
```

## ログディレクトリ構造

```
apps/admin-tool/
└── logs/
    ├── operation.log      # 現在の操作ログ
    ├── operation.log.1.zip # ローテーション済み（圧縮）
    ├── error.log          # 現在のエラーログ
    └── error.log.1.zip    # ローテーション済み（圧縮）
```

---

# Part 2: ユーザー向けシステム (Next.js)

## 技術スタック

- **Loggerライブラリ**: Pino
- **ログフォーマット**: JSON
- **環境別設定**:
  - 開発環境: pretty print（pino-pretty）
  - 本番環境: JSON形式（Vercel最適化）

## ログレベル

| レベル | 用途 | 使用例 |
|-------|------|--------|
| `debug` | 詳細なデバッグ情報 | APIリクエスト詳細、処理ステップ |
| `info` | 一般的な情報 | 申請完了、データ取得成功 |
| `warn` | 警告 | 設定不足、リトライ可能なエラー |
| `error` | エラー | 申請失敗、システムエラー |

## ログフォーマット

### JSON形式（本番環境）

```json
{
  "level": "info",
  "time": "2025-12-19T08:15:30.123Z",
  "pid": 1234,
  "hostname": "vercel-app",
  "service": "pbap-user-app",
  "version": "1.0.0",
  "env": "production",
  "component": "createTask",
  "requestId": "req_1705690130123_abc123",
  "taskId": "550e8400-e29b-41d4-a716-446655440000",
  "applicationNumber": 10001,
  "email": "user@example.com",
  "duration": 245,
  "msg": "Task created successfully"
}
```

### Pretty形式（開発環境）

```
[8:15:30.123Z] INFO (createTask): Task created successfully
    component: "createTask"
    requestId: "req_1705690130123_abc123"
    taskId: "550e8400-e29b-41d4-a716-446655440000"
    applicationNumber: 10001
    email: "user@example.com"
    duration: 245
```

## 主要ログイベント

### 1. 申請プロセス

#### 申請開始
```typescript
logger.info('Starting application submission', {
  requestId,
  email: formData.shippingInfo.email,
  recipientName: formData.shippingInfo.recipientName,
  partsCount: formData.selectedParts.length
})
```

#### 申請完了
```typescript
logger.info('Application completed successfully', {
  taskId: task.id,
  applicationNumber: task.application_number
})
```

#### 申請エラー
```typescript
logger.error('Application submission failed', {
  error: errorMessage,
  stack: error.stack,
  email: formData.shippingInfo.email
})
```

### 2. データベース操作

#### データ取得
```typescript
dbLogger.info('Products fetched successfully', {
  count: data.length,
  duration
})
```

#### データ作成
```typescript
dbLogger.info('Task created successfully', {
  taskId,
  applicationNumber: data.application_number,
  duration
})
```

#### DBエラー
```typescript
dbLogger.error('Failed to create task', {
  taskId,
  error: error.message,
  code: error.code,
  duration
})
```

### 3. APIエンドポイント

#### メール送信リクエスト
```typescript
apiLogger.info('Email confirmation request received', {
  requestId,
  taskId,
  applicationNumber,
  recipientEmail: email,
  recipientName,
  productName,
  partsCount
})
```

#### PDF生成
```typescript
apiLogger.info('PDF generated successfully', {
  size: pdfBuffer.length,
  duration
})
```

#### メール送信
```typescript
apiLogger.info('Email sent successfully', {
  duration,
  hasPdfAttachment: pdfBuffer !== null
})
```

### 4. エラー処理

#### Reactエラーバウンダリー
```typescript
logger.error('React Error Boundary caught error', {
  error: error.message,
  stack: error.stack,
  componentStack: errorInfo.componentStack,
  url: window.location.href,
  userAgent: navigator.userAgent
})
```

## 検索クエリ例

### Vercel Dashboardでの検索

- **特定の申請番号**:
  ```
  jsonPayload.applicationNumber="10001"
  ```

- **特定のユーザーの申請**:
  ```
  jsonPayload.email="user@example.com"
  ```

- **エラーのみ**:
  ```
  level="error"
  ```

- **特定の期間**:
  ```
  timestamp>="2025-12-19" AND timestamp<="2025-12-20"
  ```

- **PDF生成エラー**:
  ```
  jsonPayload.message="PDF generation failed"
  ```

### Vercel CLIでの検索

```bash
# 過去24時間の全ログ
npx vercel logs

# 特定の申請番号
npx vercel logs --filter='jsonPayload.applicationNumber="10001"'

# エラーのみ
npx vercel logs --filter='level="error"'

# リアルタイム監視
npx vercel logs --follow
```

## 設定

### 環境変数

| 変数名 | 説明 | デフォルト値 |
|-------|------|------------|
| `NODE_ENV` | 環境指定 | `development` |
| `NEXT_PUBLIC_APP_VERSION` | アプリバージョン | `1.0.0` |

### ロガー設定

```typescript
const logger = pino({
  level: process.env.NODE_ENV === 'development' ? 'debug' : 'info',
  transport: isDevelopment ? {
    target: 'pino-pretty',
    options: {
      colorize: true,
      translateTime: 'yyyy-mm-dd HH:MM:ss Z',
      ignore: 'pid,hostname'
    }
  } : undefined,
  base: {
    service: 'pbap-user-app',
    version: process.env.NEXT_PUBLIC_APP_VERSION || '1.0.0',
    env: process.env.NODE_ENV
  }
})
```

## セキュリティ考慮事項

1. **機密情報の記録を避ける**:
   - パスワード
   - APIキー
   - クレジットカード情報

2. **個人情報の取り扱い**:
   - メールアドレスは記録可能（問い合わせ対応のため）
   - 住所・電話番号は原則記録しない

3. **ログ保存期間**:
   - Vercel: 24時間（無料プラン）
   - 有料プランでの拡張を検討

## アラート設定（推奨）

### 重要なエラー

1. **申請失敗率が5%を超えた場合**
2. **データベース接続エラー**
3. **メール送信失敗率が10%を超えた場合**
4. **PDF生成失敗**

### モニタリング指標

1. **申請処理時間**（目標: <5秒）
2. **成功率**（目標: >95%）
3. **エラーレート**
4. **PDF生成時間**（目標: <10秒）

## トラブルシューティング

### よくあるログパターン

1. **申請失敗の調査**:
   ```
   level="error" AND jsonPayload.component="application-submission"
   → 申請エラーの詳細を確認
   ```

2. **パフォーマンス低下**:
   ```
   jsonPayload.duration>5000
   → 5秒以上の処理を調査
   ```

3. **メール不達**:
   ```
   jsonPayload.message="Error sending email"
   → SMTP設定の確認
   ```

## 将来的な改善案

1. **ログ集約サービス導入**:
   - Datadog
   - New Relic
   - LogRocket

2. **構造化モニタリング**:
   - 申請コンバージョン率
   - エンドポイントごとの成功/失敗率

3. **アラート自動化**:
   - Slack通知
   - メール通知

## 更新履歴

- 2025-12-19: 初版作成（ユーザー向けシステム）
- 2025-12-21: 管理ツールのログ仕様を追加（Loguru）
- Phase 1実装完了（基本ロギング機能）