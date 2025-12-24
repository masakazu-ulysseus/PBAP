# テスト仕様書

## 1. テストフレームワーク構成

| 種別 | フレームワーク | 設定ファイル |
|------|---------------|-------------|
| ユニットテスト | Vitest + React Testing Library | `vitest.config.ts` |
| E2Eテスト | Playwright | `playwright.config.ts` |

### 依存パッケージ

**ユニットテスト:**
- `vitest` - テストランナー
- `@vitejs/plugin-react` - React サポート
- `@testing-library/react` - React コンポーネントテスト
- `@testing-library/jest-dom` - DOM アサーション拡張
- `happy-dom` - 軽量 DOM 環境

**E2Eテスト:**
- `@playwright/test` - ブラウザ自動化テスト

---

## 2. ユニットテスト

### 2.1 warranty.test.ts (16テスト)

**ファイル:** `src/lib/warranty.test.ts`

#### チェックデジット計算 (`calculateCheckDigit`)

| テストケース | 入力 | 期待値 |
|-------------|------|--------|
| 5桁の数字からチェックデジット計算 | `10000` | `3` |
| 先頭が0の数字の処理 | `00001` | `0` |
| 全て9の数字の処理 | `99999` | `5` |

#### 保証コード検証 (`validateWarrantyCode`)

| テストケース | 入力 | 期待値 |
|-------------|------|--------|
| 有効なコードを受け入れ | `100003` | `true` |
| 無効なチェックデジットを拒否 | `100001` | `false` |
| 6桁未満を拒否 | `12345` | `false` |
| 6桁超を拒否 | `1234567` | `false` |
| 空文字を拒否 | `""` | `false` |
| 数字以外を拒否 | `12345a` | `false` |
| 先頭が0のコードを検証 | `000010` | `true` |
| 全て9のコードを検証 | `999995` | `true` |

#### 保証コード生成 (`generateWarrantyCode`)

| テストケース | 入力 | 期待値 |
|-------------|------|--------|
| 有効なコード生成 | - | 生成コードが検証を通過 |
| 6桁の数字を生成 | - | `/^\d{6}$/` にマッチ |
| 連番からコード生成 | `1` | `000010` |
| 大きい番号からコード生成 | `99999` | `999995` |
| 5桁を超える番号でエラー | `100000` | `Error` |

---

### 2.2 supabase.test.ts (11テスト)

**ファイル:** `src/lib/supabase.test.ts`

#### 製品取得 (`getProducts`)

| テストケース | 説明 |
|-------------|------|
| 製品一覧を正常取得 | モックデータが正しく返却される |
| エラー時に例外スロー | DBエラー時に適切な例外をスロー |

#### シリーズ取得 (`getSeries`)

| テストケース | 説明 |
|-------------|------|
| ユニークなシリーズ名をソートして返却 | 重複排除・アルファベット順ソート |
| 空のシリーズ名をフィルタ | `""`, `null` を除外 |

#### 国名取得 (`getCountries`)

| テストケース | 説明 |
|-------------|------|
| ユニークな国名をソートして返却 | 重複排除・アルファベット順ソート |

#### タスク作成 (`createTask`)

| テストケース | 説明 |
|-------------|------|
| 正しいデータでタスク作成 | 必須フィールドが正しく保存される |
| エラー時にフォーマット済みメッセージでスロー | エラーコード付きメッセージ |

#### タスク詳細作成 (`createTaskDetails`)

| テストケース | 説明 |
|-------------|------|
| 複数詳細を正常作成 | バルクインサートが成功 |
| エラー時にフォーマット済みメッセージでスロー | エラーコード付きメッセージ |

#### 組立ページ取得 (`getAssemblyPages`)

| テストケース | 説明 |
|-------------|------|
| 製品IDから組立ページ取得 | product_id でフィルタ、ページ順ソート |

#### 組立画像取得 (`getAssemblyImages`)

| テストケース | 説明 |
|-------------|------|
| ページIDから組立画像取得 | page_id でフィルタ、組立番号順ソート |

---

### 2.3 generate-pdf/route.test.ts (7テスト)

**ファイル:** `src/app/api/generate-pdf/route.test.ts`

| テストケース | 説明 | 期待結果 |
|-------------|------|----------|
| PDF正常生成 | 有効なリクエストでPDF生成 | ステータス200、Content-Type: application/pdf |
| 画像なしパーツの処理 | partImageUrl が null | fetch 未呼び出し、PDF生成成功 |
| 画像取得失敗時のグレースフル処理 | 画像URLが404 | PDF生成成功（画像なし） |
| ネットワークエラー時の処理 | fetch がエラー | PDF生成成功（画像なし） |
| WebP→PNG変換 | WebP画像のパーツ | sharp でPNG変換 |
| PDF生成エラー時に500返却 | renderToBuffer がエラー | ステータス500 |
| Content-Dispositionヘッダー設定 | 正常リクエスト | `attachment; filename="application_task-123.pdf"` |

---

### 2.4 send-confirmation/route.test.ts (6テスト)

**ファイル:** `src/app/api/send-confirmation/route.test.ts`

| テストケース | 説明 | 期待結果 |
|-------------|------|----------|
| PDF添付でメール送信成功 | PDF生成成功時 | 添付ファイル1件、送信成功 |
| PDF生成失敗時は添付なしで送信 | PDF API が 500 | 添付ファイル0件、送信成功 |
| SMTP未設定時はスキップ | SMTP_HOST 未設定 | `{ success: true, skipped: true }` |
| メール送信失敗時に500返却 | sendMail がエラー | ステータス500 |
| PDFタイムアウト時のグレースフル処理 | fetch がタイムアウト | メール送信成功（添付なし） |
| メール本文の内容確認 | 正常リクエスト | 名前・申請番号・製品名・点数を含む |

---

## 3. E2Eテスト

### 3.1 home.spec.ts (3テスト)

**ファイル:** `e2e/home.spec.ts`

| テストケース | 説明 | 検証項目 |
|-------------|------|----------|
| ホームページ表示 | `/` にアクセス | h1要素、CTAボタン表示 |
| /applyへのナビゲーション | CTAボタンクリック | URL が `/apply` に遷移 |
| ページタイトル確認 | メタデータ検証 | title に "PANZER BLOCKS" または "パーツ申請" |

---

### 3.2 application-flow.spec.ts (9テスト)

**ファイル:** `e2e/application-flow.spec.ts`

#### 申請フロー (7テスト)

| テストケース | 説明 | 検証項目 |
|-------------|------|----------|
| ステップ1デフォルト表示 | `/apply` にアクセス | 「配送先情報」、必須フィールド表示 |
| 空フォーム送信時のバリデーション | 未入力で次へ | エラーメッセージ表示 |
| ステップ1→2への遷移 | 全フィールド入力後 | 「購入情報」画面に遷移 |
| ステップ2→1への戻り | 戻るボタンクリック | 「配送先情報」に戻り、入力値保持 |
| 部品保証コードバリデーション | 5桁入力で次へ | 6桁エラーメッセージ表示 |
| ステップインジケーター表示 | 画面表示確認 | 「ステップ」または「Step」表示 |
| ステップ2のローディング状態 | ステップ2遷移時 | 10秒以内に「購入情報」表示 |

#### アクセシビリティ (2テスト)

| テストケース | 説明 | 検証項目 |
|-------------|------|----------|
| フォームラベルの関連付け | label-input 紐付け | getByLabel で入力可能 |
| キーボードナビゲーション | Tab キー操作 | フォーカス移動可能 |

---

## 4. テスト実行コマンド

### ユニットテスト

```bash
# ウォッチモード（ファイル変更で自動再実行）
npm run test

# 単発実行
npm run test:run

# カバレッジレポート付き
npm run test:coverage
```

### E2Eテスト

```bash
# ヘッドレス実行
npm run e2e

# UIモード（インタラクティブ）
npm run e2e:ui

# ブラウザ表示して実行
npm run e2e:headed

# デバッグモード
npm run e2e:debug
```

---

## 5. テスト統計

| カテゴリ | テスト数 | ファイル数 |
|---------|---------|-----------|
| warranty.test.ts | 16 | 1 |
| supabase.test.ts | 11 | 1 |
| generate-pdf/route.test.ts | 7 | 1 |
| send-confirmation/route.test.ts | 6 | 1 |
| **ユニットテスト合計** | **40** | **4** |
| home.spec.ts | 3 | 1 |
| application-flow.spec.ts | 9 | 1 |
| **E2Eテスト合計** | **12** | **2** |
| **総合計** | **52** | **6** |

---

## 6. モック設定

### 6.1 共通モック

**logger モック:**
```typescript
vi.mock('@/lib/logger', () => ({
  createChildLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
  generateRequestId: () => 'test-request-id',
}))
```

### 6.2 supabase.test.ts

- `@supabase/supabase-js` のチェーン可能なモック
- `from`, `select`, `insert`, `eq`, `not`, `order`, `single` メソッド

### 6.3 generate-pdf/route.test.ts

- `@react-pdf/renderer` - Document, Page, Text, View, renderToBuffer
- `sharp` - PNG変換
- `fs` - ファイル操作
- `fetch` - 画像取得

### 6.4 send-confirmation/route.test.ts

- `nodemailer` - createTransport, sendMail
- `fetch` - PDF生成API呼び出し

---

## 7. セットアップ要件

### 7.1 ユニットテスト

特別なセットアップ不要。`npm install` 後すぐに実行可能。

### 7.2 E2Eテスト

ブラウザ実行に必要なシステムライブラリをインストール:

```bash
# Chromium の依存関係インストール（要sudo）
sudo npx playwright install-deps chromium
```

### 7.3 CI/CD環境

GitHub Actions の場合、公式 Playwright アクションを使用:

```yaml
- name: Install Playwright Browsers
  run: npx playwright install --with-deps chromium
```

---

## 8. 設定ファイル

### 8.1 vitest.config.ts

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        'src/components/ui/**'
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

### 8.2 playwright.config.ts

```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
})
```

---

## 9. テスト作成ガイドライン

### 9.1 ユニットテスト

1. **ファイル命名**: `*.test.ts` または `*.test.tsx`
2. **配置**: テスト対象ファイルと同じディレクトリ
3. **モック**: 外部依存（DB、API、ファイルシステム）は必ずモック
4. **カバレッジ**: 主要なビジネスロジックは100%を目指す

### 9.2 E2Eテスト

1. **ファイル命名**: `*.spec.ts`
2. **配置**: `e2e/` ディレクトリ
3. **スコープ**: ユーザーシナリオベースのテスト
4. **安定性**: 適切なタイムアウトとリトライ設定
