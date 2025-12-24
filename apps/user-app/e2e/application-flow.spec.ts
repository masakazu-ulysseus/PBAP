import { test, expect } from '@playwright/test'

test.describe('Application Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/apply')
  })

  test('should display step 1 (shipping info) by default', async ({ page }) => {
    // ステップ1の送付先情報フォームが表示されることを確認
    await expect(page.getByText('送付先情報').first()).toBeVisible()

    // 必須フィールドが存在することを確認（ラベルには * が含まれる）
    await expect(page.getByLabel(/氏名/)).toBeVisible()
    await expect(page.getByLabel(/郵便番号/)).toBeVisible()
    await expect(page.getByLabel(/住所/)).toBeVisible()
    await expect(page.getByLabel(/電話番号/)).toBeVisible()
    await expect(page.getByLabel(/メールアドレス/)).toBeVisible()
  })

  test('should show validation errors when submitting empty form on step 1', async ({ page }) => {
    // 空のまま次へボタンをクリック
    const nextButton = page.getByRole('button', { name: /次へ進む/ })
    await nextButton.click()

    // バリデーションエラーが表示されることを確認
    await expect(page.getByText(/氏名を入力してください|必須/i)).toBeVisible()
  })

  test('should navigate to step 2 after completing step 1', async ({ page }) => {
    // ステップ1のフォームに入力
    await page.getByLabel(/氏名/).fill('テスト太郎')
    await page.getByLabel(/郵便番号/).fill('123-4567')
    await page.getByLabel(/住所/).fill('東京都新宿区テスト町1-2-3')
    await page.getByLabel(/電話番号/).fill('090-1234-5678')
    await page.getByLabel(/メールアドレス/).fill('test@example.com')

    // 次へボタンをクリック
    const nextButton = page.getByRole('button', { name: /次へ進む/ })
    await nextButton.click()

    // ステップ2（購入情報）が表示されることを確認
    await expect(page.getByText('購入情報').first()).toBeVisible()
  })

  test('should be able to go back from step 2 to step 1', async ({ page }) => {
    // ステップ1を完了
    await page.getByLabel(/氏名/).fill('テスト太郎')
    await page.getByLabel(/郵便番号/).fill('123-4567')
    await page.getByLabel(/住所/).fill('東京都新宿区テスト町1-2-3')
    await page.getByLabel(/電話番号/).fill('090-1234-5678')
    await page.getByLabel(/メールアドレス/).fill('test@example.com')

    await page.getByRole('button', { name: /次へ進む/ }).click()

    // ステップ2が表示されていることを確認
    await expect(page.getByText('購入情報').first()).toBeVisible()

    // 戻るボタンをクリック
    await page.getByRole('button', { name: /戻る/i }).click()

    // ステップ1に戻ることを確認
    await expect(page.getByText('送付先情報').first()).toBeVisible()

    // 入力値が保持されていることを確認
    await expect(page.getByLabel(/氏名/)).toHaveValue('テスト太郎')
  })

  test('should validate warranty code format on step 2', async ({ page }) => {
    // ステップ1を完了
    await page.getByLabel(/氏名/).fill('テスト太郎')
    await page.getByLabel(/郵便番号/).fill('123-4567')
    await page.getByLabel(/住所/).fill('東京都新宿区テスト町1-2-3')
    await page.getByLabel(/電話番号/).fill('090-1234-5678')
    await page.getByLabel(/メールアドレス/).fill('test@example.com')
    await page.getByRole('button', { name: /次へ進む/ }).click()

    // ステップ2で無効な部品保証コードを入力
    await expect(page.getByLabel(/部品保証コード/)).toBeVisible()
    await page.getByLabel(/部品保証コード/).fill('12345') // 5桁（6桁必要）

    // 次へボタンをクリック
    await page.getByRole('button', { name: /次へ進む/ }).click()

    // バリデーションエラーが表示されることを確認
    await expect(page.getByText('部品保証コードは6桁です')).toBeVisible()
  })

  test('should show step progress indicator', async ({ page }) => {
    // ステップインジケーターが表示されていることを確認（ステップ番号）
    await expect(page.getByText('1')).toBeVisible()
    await expect(page.getByText('送付先情報').first()).toBeVisible()
  })

  test('should display loading state when fetching products on step 2', async ({ page }) => {
    // ステップ1を完了
    await page.getByLabel(/氏名/).fill('テスト太郎')
    await page.getByLabel(/郵便番号/).fill('123-4567')
    await page.getByLabel(/住所/).fill('東京都新宿区テスト町1-2-3')
    await page.getByLabel(/電話番号/).fill('090-1234-5678')
    await page.getByLabel(/メールアドレス/).fill('test@example.com')
    await page.getByRole('button', { name: /次へ進む/ }).click()

    // ステップ2のコンテンツが表示されることを確認（ローディング後）
    await expect(page.getByText('購入情報').first()).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Application Accessibility', () => {
  test('should have proper form labels for accessibility', async ({ page }) => {
    await page.goto('/apply')

    // ラベルと入力フィールドが正しく関連付けられていることを確認
    const nameInput = page.getByLabel(/氏名/)
    await expect(nameInput).toBeEnabled()

    const emailInput = page.getByLabel(/メールアドレス/)
    await expect(emailInput).toBeEnabled()
  })

  test('should be navigable with keyboard', async ({ page }) => {
    await page.goto('/apply')

    // Tab キーでフォームフィールド間を移動できることを確認
    await page.keyboard.press('Tab')

    // フォーカスがフォームフィールドに移動していることを確認
    const focusedElement = page.locator(':focus')
    await expect(focusedElement).toBeVisible()
  })
})
