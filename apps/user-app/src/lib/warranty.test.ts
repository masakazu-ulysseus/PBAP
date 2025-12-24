import { describe, it, expect } from 'vitest'
import {
  calculateCheckDigit,
  validateWarrantyCode,
  generateWarrantyCode,
} from './warranty'

describe('warranty', () => {
  describe('calculateCheckDigit', () => {
    it('should calculate check digit for 10000', () => {
      // d1*8 + d2*7 + d3*6 + d4*5 + d5*4
      // 1*8 + 0*7 + 0*6 + 0*5 + 0*4 = 8
      // MOD(11 - MOD(8, 11), 10) = MOD(11 - 8, 10) = MOD(3, 10) = 3
      expect(calculateCheckDigit('10000')).toBe(3)
    })

    it('should calculate check digit for 12345', () => {
      // 1*8 + 2*7 + 3*6 + 4*5 + 5*4 = 8 + 14 + 18 + 20 + 20 = 80
      // MOD(11 - MOD(80, 11), 10) = MOD(11 - 3, 10) = MOD(8, 10) = 8
      expect(calculateCheckDigit('12345')).toBe(8)
    })

    it('should calculate check digit for 99999', () => {
      // 9*8 + 9*7 + 9*6 + 9*5 + 9*4 = 72 + 63 + 54 + 45 + 36 = 270
      // MOD(11 - MOD(270, 11), 10) = MOD(11 - 6, 10) = MOD(5, 10) = 5
      expect(calculateCheckDigit('99999')).toBe(5)
    })

    it('should calculate check digit for 00000', () => {
      // 0*8 + 0*7 + 0*6 + 0*5 + 0*4 = 0
      // MOD(11 - MOD(0, 11), 10) = MOD(11 - 0, 10) = MOD(11, 10) = 1
      expect(calculateCheckDigit('00000')).toBe(1)
    })

    it('should throw error for non-5-digit input', () => {
      expect(() => calculateCheckDigit('1234')).toThrow('番号は5桁である必要があります')
      expect(() => calculateCheckDigit('123456')).toThrow('番号は5桁である必要があります')
      expect(() => calculateCheckDigit('')).toThrow('番号は5桁である必要があります')
    })
  })

  describe('validateWarrantyCode', () => {
    it('should return true for valid warranty code 100003', () => {
      expect(validateWarrantyCode('100003')).toBe(true)
    })

    it('should return true for valid warranty code 123458', () => {
      expect(validateWarrantyCode('123458')).toBe(true)
    })

    it('should return true for valid warranty code 999995', () => {
      expect(validateWarrantyCode('999995')).toBe(true)
    })

    it('should return false for invalid check digit', () => {
      expect(validateWarrantyCode('100000')).toBe(false)
      expect(validateWarrantyCode('100001')).toBe(false)
      expect(validateWarrantyCode('100002')).toBe(false)
      expect(validateWarrantyCode('100004')).toBe(false)
    })

    it('should return false for non-6-digit input', () => {
      expect(validateWarrantyCode('12345')).toBe(false)
      expect(validateWarrantyCode('1234567')).toBe(false)
      expect(validateWarrantyCode('')).toBe(false)
    })

    it('should return false for non-numeric input', () => {
      expect(validateWarrantyCode('12345a')).toBe(false)
      expect(validateWarrantyCode('abcdef')).toBe(false)
      expect(validateWarrantyCode('12-456')).toBe(false)
    })
  })

  describe('generateWarrantyCode', () => {
    it('should generate warranty code for 10000', () => {
      expect(generateWarrantyCode('10000')).toBe('100003')
    })

    it('should generate warranty code for 12345', () => {
      expect(generateWarrantyCode('12345')).toBe('123458')
    })

    it('should generate warranty code for 99999', () => {
      expect(generateWarrantyCode('99999')).toBe('999995')
    })

    it('should generate warranty code for 00000', () => {
      expect(generateWarrantyCode('00000')).toBe('000001')
    })

    it('generated codes should pass validation', () => {
      const testNumbers = ['10000', '12345', '54321', '99999', '00000', '11111']
      for (const num of testNumbers) {
        const code = generateWarrantyCode(num)
        expect(validateWarrantyCode(code)).toBe(true)
      }
    })
  })
})
