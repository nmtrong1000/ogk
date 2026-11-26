import { useState, type FormEvent, type ReactNode } from 'react'
import { Button, Select, TextField } from '@/shared/components/index.ts'
import { useToast } from '@/shared/components/ToastContext.ts'
import { ToastMessage } from '@/shared/components/ToastProvider.tsx'
import type { ChildInput } from '@/shared/types/family.ts'
import { MAX_NAME_LENGTH, MIN_BIRTH_YEAR, errorMessage, fieldError } from '@/features/family/utils/messages.ts'
import { currentYear } from '@/features/family/utils/year.ts'
import { childFormSchema } from '@/features/family/schemas.ts'

type Props = {
  initial?: ChildInput
  submitLabel: string
  pending: boolean
  error: unknown
  onSubmit: (body: ChildInput) => void
  onCancel?: () => void
  secondaryAction?: ReactNode
  inlineErrors?: boolean
}

function yearOptions() {
  const options = []
  for (let year = currentYear(); year >= MIN_BIRTH_YEAR; year--)
    options.push({ value: String(year), label: String(year) })
  return options
}

export default function ChildForm({
  initial,
  submitLabel,
  pending,
  error,
  onSubmit,
  onCancel,
  secondaryAction,
  inlineErrors = false,
}: Props) {
  const showToast = useToast()
  const [name, setName] = useState(initial?.name ?? '')
  const [birthYear, setBirthYear] = useState(initial ? String(initial.birth_year) : '')
  const [validationError, setValidationError] = useState<{ field: 'name' | 'birthYear'; message: string } | null>(null)

  function submit(event: FormEvent) {
    event.preventDefault()
    const result = childFormSchema.safeParse({ name, birthYear })
    if (!result.success) {
      const issue = result.error.issues[0]
      if (inlineErrors && (issue.path[0] === 'name' || issue.path[0] === 'birthYear')) {
        setValidationError({ field: issue.path[0], message: issue.message })
      } else {
        showToast({ tone: 'error', message: issue.message })
      }
      return
    }
    setValidationError(null)
    onSubmit(result.data)
  }

  const server = fieldError(error)
  const showAlert = error != null && !server.name && !server.birthYear
  const nameError = validationError?.field === 'name' ? validationError.message : server.name
  const birthYearError = validationError?.field === 'birthYear' ? validationError.message : server.birthYear

  return (
    <form className="flex flex-col gap-4" onSubmit={submit} noValidate>
      {showAlert &&
        (inlineErrors ? (
          <p role="alert" className="text-xs text-rose-700">
            {errorMessage(error)}
          </p>
        ) : (
          <ToastMessage tone="error">{errorMessage(error)}</ToastMessage>
        ))}
      <div className="grid gap-4 sm:grid-cols-[1fr_12rem]">
        <TextField
          label="Tên con"
          autoComplete="off"
          maxLength={MAX_NAME_LENGTH}
          required
          value={name}
          error={nameError}
          errorMode={inlineErrors ? 'inline' : 'toast'}
          onChange={(e) => {
            if (validationError?.field === 'name') setValidationError(null)
            setName(e.target.value)
          }}
        />
        <Select
          label="Năm sinh"
          required
          placeholder="Chọn năm"
          options={yearOptions()}
          value={birthYear}
          error={birthYearError}
          errorMode={inlineErrors ? 'inline' : 'toast'}
          onChange={(e) => {
            if (validationError?.field === 'birthYear') setValidationError(null)
            setBirthYear(e.target.value)
          }}
        />
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2">
        {secondaryAction}
        {onCancel && (
          <Button variant="ghost" onClick={onCancel} disabled={pending}>
            Hủy
          </Button>
        )}
        <Button type="submit" loading={pending}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}
