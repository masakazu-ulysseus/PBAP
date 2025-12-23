/**
 * 保証コード検証ユーティリティ
 *
 * チェックデジット計算式:
 * MOD(11 - MOD(d1*8 + d2*7 + d3*6 + d4*5 + d5*4, 11), 10)
 *
 * 例: 10000 → チェックデジット 3 → 保証コード 100003
 */

/**
 * 5桁の番号からチェックデジットを計算
 * @param number 5桁の番号（文字列）
 * @returns チェックデジット（0-9）
 */
export function calculateCheckDigit(number: string): number {
  if (number.length !== 5) {
    throw new Error('番号は5桁である必要があります')
  }

  const digits = number.split('').map(Number)

  // 各桁に重みを掛けて合計
  // d1*8 + d2*7 + d3*6 + d4*5 + d5*4
  const weights = [8, 7, 6, 5, 4]
  const weightedSum = digits.reduce((sum, digit, index) => {
    return sum + digit * weights[index]
  }, 0)

  // MOD(11 - MOD(weightedSum, 11), 10)
  const checkDigit = (11 - (weightedSum % 11)) % 10

  return checkDigit
}

/**
 * 保証コードが有効かどうかを検証
 * @param warrantyCode 6桁の保証コード（5桁の番号 + 1桁のチェックデジット）
 * @returns 有効な場合true
 */
export function validateWarrantyCode(warrantyCode: string): boolean {
  // 数字のみで6桁かチェック
  if (!/^\d{6}$/.test(warrantyCode)) {
    return false
  }

  const number = warrantyCode.slice(0, 5)
  const providedCheckDigit = parseInt(warrantyCode.slice(5), 10)

  try {
    const calculatedCheckDigit = calculateCheckDigit(number)
    return calculatedCheckDigit === providedCheckDigit
  } catch {
    return false
  }
}

/**
 * 番号から完全な保証コードを生成
 * @param number 5桁の番号
 * @returns 6桁の保証コード
 */
export function generateWarrantyCode(number: string): string {
  const checkDigit = calculateCheckDigit(number)
  return `${number}${checkDigit}`
}
