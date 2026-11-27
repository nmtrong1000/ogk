import { describe, expect, it } from 'vitest'
import { loginFormSchema, registerFormSchema } from '@/features/auth/schemas.ts'
import { appRuleFormSchema } from '@/features/appcontrol/schemas.ts'
import { childFormSchema } from '@/features/family/schemas.ts'
import {
  appGroupBudgetInputSchema,
  appGroupNameSchema,
  appGroupsSchema,
  quotaFormSchema,
  weeklyScheduleSchema,
} from '@/features/screentime/schemas.ts'

describe('authentication form schemas', () => {
  it('rejects missing login values and normalizes email', () => {
    expect(loginFormSchema.safeParse({ email: '', password: '' }).success).toBe(false)
    expect(loginFormSchema.parse({ email: ' parent@example.com ', password: 'password' })).toEqual({
      email: 'parent@example.com',
      password: 'password',
    })
  })

  it('checks registration password length and confirmation', () => {
    expect(
      registerFormSchema.safeParse({ email: 'parent@example.com', password: 'short', confirmPassword: 'short' })
        .success,
    ).toBe(false)
    expect(
      registerFormSchema.safeParse({
        email: 'parent@example.com',
        password: 'long-enough-password',
        confirmPassword: 'different-password',
      }).success,
    ).toBe(false)
  })
})

describe('family form schema', () => {
  it('trims the child name and parses the birth year', () => {
    expect(childFormSchema.parse({ name: ' Bé An ', birthYear: '2017' })).toEqual({ name: 'Bé An', birth_year: 2017 })
    expect(childFormSchema.safeParse({ name: ' ', birthYear: '2017' }).success).toBe(false)
  })
})

describe('application rule form schema', () => {
  const groups = [{ id: 'games', name: 'Trò chơi', budget_minutes: null }]

  it('normalizes valid rules and rejects duplicate entries', () => {
    const rule = { name: ' GAME.EXE ', sha: '', action: 'block', groupId: 'games' }
    expect(appRuleFormSchema([], groups).parse(rule)).toEqual({
      name: 'game.exe',
      sha256: null,
      action: 'block',
      group_id: 'games',
    })
    expect(
      appRuleFormSchema([{ name: 'game.exe', sha256: null, action: 'block', group_id: 'games' }], groups).safeParse(
        rule,
      ).success,
    ).toBe(false)
  })
})

describe('screen time form schemas', () => {
  it('converts quota parts to minutes and rejects invalid minute values', () => {
    expect(
      quotaFormSchema.parse({ weekday: { hours: '3', minutes: '30' }, weekend: { hours: '0', minutes: '0' } }),
    ).toEqual({ weekday: 210, weekend: 0 })
    expect(
      quotaFormSchema.safeParse({ weekday: { hours: '2', minutes: '60' }, weekend: { hours: '1', minutes: '0' } })
        .success,
    ).toBe(false)
  })

  it('accepts only a full seven-day schedule', () => {
    expect(weeklyScheduleSchema.safeParse(Array.from({ length: 7 }, () => '0'.repeat(48))).success).toBe(true)
    expect(weeklyScheduleSchema.safeParse(['0'.repeat(48)]).success).toBe(false)
  })

  it('validates new group names, budgets and the full group list', () => {
    const groups = [{ id: 'games', name: 'Trò chơi', budget_minutes: null }]
    expect(appGroupNameSchema(groups).safeParse('trò CHƠI').success).toBe(false)
    expect(appGroupBudgetInputSchema.parse('1440')).toBe(1440)
    expect(appGroupBudgetInputSchema.safeParse('1441').success).toBe(false)
    expect(appGroupsSchema.safeParse(groups).success).toBe(true)
  })
})
