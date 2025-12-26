/**
 * ZipCloud API ユーティリティ
 * 郵便番号から住所を検索する
 * @see http://zipcloud.ibsnet.co.jp/doc/api
 */

export interface ZipCloudAddress {
  zipcode: string
  prefcode: string    // 都道府県コード
  address1: string    // 都道府県
  address2: string    // 市区町村
  address3: string    // 町域
  kana1: string       // 都道府県カナ
  kana2: string       // 市区町村カナ
  kana3: string       // 町域カナ
}

export interface ZipCloudResponse {
  status: number
  message: string | null
  results: ZipCloudAddress[] | null
}

/**
 * 郵便番号から住所を検索
 * @param zipCode 郵便番号（ハイフンあり/なしどちらも可）
 * @returns 住所の配列（複数件の場合あり）
 */
export async function searchAddressByZipCode(
  zipCode: string
): Promise<ZipCloudAddress[]> {
  // ハイフンを除去して7桁の数字のみにする
  const normalizedZipCode = zipCode.replace(/-/g, '')

  // 7桁でない場合は空配列を返す
  if (!/^\d{7}$/.test(normalizedZipCode)) {
    return []
  }

  try {
    const response = await fetch(
      `https://zipcloud.ibsnet.co.jp/api/search?zipcode=${normalizedZipCode}`
    )

    if (!response.ok) {
      console.error('ZipCloud API error:', response.status)
      return []
    }

    const data: ZipCloudResponse = await response.json()

    if (data.status !== 200) {
      console.error('ZipCloud API error:', data.message)
      return []
    }

    return data.results ?? []
  } catch (error) {
    console.error('ZipCloud API fetch error:', error)
    return []
  }
}

/**
 * 郵便番号をフォーマット（表示用）
 * @param zipCode 郵便番号
 * @returns フォーマット済み郵便番号（例: 123-4567）
 */
export function formatZipCode(zipCode: string): string {
  const digits = zipCode.replace(/\D/g, '')
  if (digits.length >= 7) {
    return `${digits.slice(0, 3)}-${digits.slice(3, 7)}`
  }
  return digits
}

/**
 * 郵便番号の正規化（保存用）
 * @param zipCode 郵便番号
 * @returns ハイフンなしの7桁数字
 */
export function normalizeZipCode(zipCode: string): string {
  return zipCode.replace(/\D/g, '').slice(0, 7)
}
