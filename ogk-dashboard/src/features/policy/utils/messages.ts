import { commonErrorMessage } from '@/shared/api/errors.ts'

export function policyErrorMessage(error: unknown): string {
  return commonErrorMessage(error)
}

export function setterLabel(email: string | null): string {
  return email ?? 'Tài khoản đã xóa'
}
