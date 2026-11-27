import { z } from 'zod'
import type { AppGroup } from '@/shared/types/policy.ts'
import { MAX_QUOTA_MINUTES, QUOTA_ERROR } from '@/features/screentime/utils/messages.ts'

const quotaPartSchema = z
  .object({
    hours: z.string().regex(/^\d{1,2}$/, QUOTA_ERROR),
    minutes: z.string().regex(/^\d{1,2}$/, QUOTA_ERROR),
  })
  .superRefine(({ hours, minutes }, context) => {
    const total = Number(hours) * 60 + Number(minutes)
    if (Number(minutes) >= 60 || total > MAX_QUOTA_MINUTES) {
      context.addIssue({ code: 'custom', path: ['minutes'], message: QUOTA_ERROR })
    }
  })
  .transform(({ hours, minutes }) => Number(hours) * 60 + Number(minutes))

export const quotaFormSchema = z.object({ weekday: quotaPartSchema, weekend: quotaPartSchema })

export const weeklyScheduleSchema = z
  .array(z.string().regex(/^[01]{48}$/, 'Mỗi ngày cần có đủ 48 khung giờ.'))
  .length(7, 'Lịch tuần cần có đủ 7 ngày.')

const groupNameSchema = z
  .string()
  .trim()
  .min(1, 'Tên nhóm không được để trống.')
  .max(40, 'Tên nhóm dài tối đa 40 ký tự.')

export function appGroupNameSchema(groups: AppGroup[]) {
  return groupNameSchema.refine(
    (name) => !groups.some((group) => group.name.toLocaleLowerCase() === name.toLocaleLowerCase()),
    'Tên nhóm phải chưa được sử dụng.',
  )
}

export const appGroupBudgetInputSchema = z
  .string()
  .regex(/^\d*$/, QUOTA_ERROR)
  .transform((value) => (value === '' ? null : Number(value)))
  .refine(
    (value) => value === null || (Number.isInteger(value) && value >= 0 && value <= MAX_QUOTA_MINUTES),
    QUOTA_ERROR,
  )

export const appGroupsSchema = z
  .array(
    z.object({
      id: z.string().min(1),
      name: groupNameSchema,
      budget_minutes: z.number().int().min(0).max(MAX_QUOTA_MINUTES).nullable(),
    }),
  )
  .superRefine((groups, context) => {
    const names = new Set<string>()
    groups.forEach((group, index) => {
      const normalized = group.name.toLocaleLowerCase()
      if (names.has(normalized)) {
        context.addIssue({ code: 'custom', path: [index, 'name'], message: 'Tên nhóm phải chưa được sử dụng.' })
      }
      names.add(normalized)
    })
  })
