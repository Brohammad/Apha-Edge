import { describe, expect, it } from 'vitest'
import { fmtMoney, fmtNum, fmtPct, shortId, signClass } from './format'

describe('fmtMoney', () => {
  it('formats USD', () => {
    expect(fmtMoney(999.5)).toMatch(/\$999\.50/)
  })
  it('returns dash for empty', () => {
    expect(fmtMoney(null)).toBe('—')
    expect(fmtMoney('')).toBe('—')
  })
})

describe('fmtNum / fmtPct', () => {
  it('formats numbers', () => {
    expect(fmtNum(1.2345, 2)).toBe('1.23')
  })
  it('formats percentages', () => {
    expect(fmtPct(0.125, 1)).toBe('12.5%')
  })
})

describe('signClass / shortId', () => {
  it('picks bull/bear classes', () => {
    expect(signClass(1)).toContain('bull')
    expect(signClass(-1)).toContain('bear')
  })
  it('shortens ids', () => {
    expect(shortId('abcdefghij')).toBe('abcdefgh')
  })
})
