import { z } from 'zod'
import type { AppGroup, AppRule } from '@/shared/types/policy.ts'
import {
  DUPLICATE_ERROR,
  LIMIT_ERROR,
  MAX_APP_RULES,
  NAME_ERROR,
  SHA_ERROR,
} from '@/features/appcontrol/utils/messages.ts'

const SHA_PATTERN = /^[0-9a-f]{64}$/

export function appRuleFormSchema(rules: AppRule[], groups: AppGroup[]) {
  return z
    .object({
      name: z
        .string()
        .trim()
        .toLowerCase()
        .min(1, NAME_ERROR)
        .max(255, NAME_ERROR)
        .refine((name) => !/[\\/]/.test(name), NAME_ERROR),
      sha: z
        .string()
        .trim()
        .toLowerCase()
        .refine((sha) => !sha || SHA_PATTERN.test(sha), SHA_ERROR)
        .transform((sha) => sha || null),
      action: z.enum(['allow', 'block']),
      groupId: z.string().refine((id) => groups.some((group) => group.id === id), 'Chọn nhóm ứng dụng hợp lệ.'),
    })
    .superRefine((value, context) => {
      if (rules.length >= MAX_APP_RULES) {
        context.addIssue({ code: 'custom', path: ['form'], message: LIMIT_ERROR })
        return
      }
      if (rules.some((rule) => rule.name === value.name && rule.sha256 === value.sha)) {
        context.addIssue({ code: 'custom', path: ['form'], message: DUPLICATE_ERROR })
      }
    })
    .transform(({ name, sha, action, groupId }) => ({
      name,
      sha256: sha,
      action,
      group_id: groupId,
    }))
}
