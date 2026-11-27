import { z } from 'zod'
import { WEB_CATEGORIES } from '@/features/webfilter/api.ts'

const DOMAIN_PATTERN = /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/

const domainSchema = z
  .string()
  .trim()
  .toLowerCase()
  .transform((domain) => domain.replace(/\.$/, ''))
  .pipe(
    z
      .string()
      .min(1, 'Nhập tên miền.')
      .max(253, 'Tên miền không được dài quá 253 ký tự.')
      .regex(DOMAIN_PATTERN, 'Tên miền không hợp lệ.'),
  )

export const catalogFormSchema = z.object({
  domain: domainSchema,
  category: z.enum(WEB_CATEGORIES),
})
