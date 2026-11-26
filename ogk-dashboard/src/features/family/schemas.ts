import { z } from 'zod'
import { BIRTH_YEAR_ERROR, MAX_NAME_LENGTH, MIN_BIRTH_YEAR, NAME_ERROR } from '@/features/family/utils/messages.ts'
import { currentYear } from '@/features/family/utils/year.ts'

export const childFormSchema = z
  .object({
    name: z.string().trim().min(1, NAME_ERROR).max(MAX_NAME_LENGTH, NAME_ERROR),
    birthYear: z
      .string()
      .regex(/^\d{4}$/, BIRTH_YEAR_ERROR)
      .transform(Number)
      .pipe(z.number().int().min(MIN_BIRTH_YEAR, BIRTH_YEAR_ERROR).max(currentYear(), BIRTH_YEAR_ERROR)),
  })
  .transform(({ name, birthYear }) => ({ name, birth_year: birthYear }))
