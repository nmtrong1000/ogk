import { describe, expect, it } from 'vitest'
import { formatDuration, formatHours } from '@/shared/utils/duration.ts'

describe('duration formatting', () => {
  it('clamps negative durations to zero', () => {
    expect(formatDuration(-12)).toBe('0 phút')
  })

  it('formats hours with remaining minutes', () => {
    expect(formatDuration(5_580)).toBe('1 giờ 33 phút')
  })

  it('formats decimal hours using Vietnamese locale', () => {
    expect(formatHours(5_400)).toBe('1,5 giờ')
  })
})
