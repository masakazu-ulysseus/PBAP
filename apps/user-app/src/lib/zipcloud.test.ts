import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  searchAddressByZipCode,
  formatZipCode,
  normalizeZipCode,
  type ZipCloudAddress,
} from './zipcloud'

// fetchをモック
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('zipcloud', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('searchAddressByZipCode', () => {
    const mockAddress: ZipCloudAddress = {
      zipcode: '1000001',
      prefcode: '13',
      address1: '東京都',
      address2: '千代田区',
      address3: '千代田',
      kana1: 'トウキョウト',
      kana2: 'チヨダク',
      kana3: 'チヨダ',
    }

    it('正常な郵便番号で住所を取得できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 200,
          message: null,
          results: [mockAddress],
        }),
      })

      const result = await searchAddressByZipCode('1000001')

      expect(mockFetch).toHaveBeenCalledWith(
        'https://zipcloud.ibsnet.co.jp/api/search?zipcode=1000001'
      )
      expect(result).toEqual([mockAddress])
    })

    it('ハイフン付き郵便番号でも正常に検索できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 200,
          message: null,
          results: [mockAddress],
        }),
      })

      const result = await searchAddressByZipCode('100-0001')

      expect(mockFetch).toHaveBeenCalledWith(
        'https://zipcloud.ibsnet.co.jp/api/search?zipcode=1000001'
      )
      expect(result).toEqual([mockAddress])
    })

    it('複数の住所が返される場合も正常に処理できる', async () => {
      const mockAddresses: ZipCloudAddress[] = [
        { ...mockAddress, address3: '千代田1' },
        { ...mockAddress, address3: '千代田2' },
      ]

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 200,
          message: null,
          results: mockAddresses,
        }),
      })

      const result = await searchAddressByZipCode('1000001')

      expect(result).toHaveLength(2)
    })

    it('7桁未満の郵便番号は空配列を返す', async () => {
      const result = await searchAddressByZipCode('123456')

      expect(mockFetch).not.toHaveBeenCalled()
      expect(result).toEqual([])
    })

    it('数字以外を含む不正な郵便番号は空配列を返す', async () => {
      const result = await searchAddressByZipCode('abc1234')

      expect(mockFetch).not.toHaveBeenCalled()
      expect(result).toEqual([])
    })

    it('存在しない郵便番号はnullが返され空配列になる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 200,
          message: null,
          results: null,
        }),
      })

      const result = await searchAddressByZipCode('0000000')

      expect(result).toEqual([])
    })

    it('APIエラー時は空配列を返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      })

      const result = await searchAddressByZipCode('1000001')

      expect(result).toEqual([])
    })

    it('ネットワークエラー時は空配列を返す', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'))

      const result = await searchAddressByZipCode('1000001')

      expect(result).toEqual([])
    })

    it('APIステータスエラー時は空配列を返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 400,
          message: 'パラメータエラー',
          results: null,
        }),
      })

      const result = await searchAddressByZipCode('1000001')

      expect(result).toEqual([])
    })
  })

  describe('formatZipCode', () => {
    it('7桁の数字をハイフン付きでフォーマットする', () => {
      expect(formatZipCode('1000001')).toBe('100-0001')
    })

    it('すでにハイフンがある場合も正しくフォーマットする', () => {
      expect(formatZipCode('100-0001')).toBe('100-0001')
    })

    it('8桁以上でも先頭7桁をフォーマットする', () => {
      expect(formatZipCode('12345678')).toBe('123-4567')
    })

    it('6桁以下はそのまま返す', () => {
      expect(formatZipCode('123456')).toBe('123456')
    })

    it('空文字は空文字を返す', () => {
      expect(formatZipCode('')).toBe('')
    })
  })

  describe('normalizeZipCode', () => {
    it('ハイフンを除去して7桁にする', () => {
      expect(normalizeZipCode('100-0001')).toBe('1000001')
    })

    it('数字のみの場合はそのまま返す', () => {
      expect(normalizeZipCode('1000001')).toBe('1000001')
    })

    it('8桁以上は先頭7桁のみ返す', () => {
      expect(normalizeZipCode('12345678')).toBe('1234567')
    })

    it('スペースや他の文字も除去する', () => {
      expect(normalizeZipCode('100 0001')).toBe('1000001')
      expect(normalizeZipCode('〒100-0001')).toBe('1000001')
    })

    it('空文字は空文字を返す', () => {
      expect(normalizeZipCode('')).toBe('')
    })
  })
})
