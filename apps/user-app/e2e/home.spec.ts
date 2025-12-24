import { test, expect } from '@playwright/test'

test.describe('Home Page', () => {
  test('should display the home page with hero section', async ({ page }) => {
    await page.goto('/')

    // ヒーローセクションが表示されることを確認
    await expect(page.locator('h1')).toBeVisible()

    // CTAボタンが存在することを確認（複数あるため.first()を使用）
    await expect(page.getByRole('link', { name: '申請を開始する' }).first()).toBeVisible()
  })

  test('should navigate to apply page when clicking CTA button', async ({ page }) => {
    await page.goto('/')

    // CTAボタンをクリック（複数あるため.first()を使用）
    await page.getByRole('link', { name: '申請を開始する' }).first().click()

    // /applyページに遷移したことを確認
    await expect(page).toHaveURL('/apply')
  })

  test('should have proper page title and metadata', async ({ page }) => {
    await page.goto('/')

    // ページタイトルが設定されていることを確認
    await expect(page).toHaveTitle(/パンツァーブロックス|部品申請/i)
  })
})
