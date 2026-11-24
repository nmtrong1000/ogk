import { ApiError } from '@/shared/api/client.ts'
import { commonErrorMessage } from '@/shared/api/errors.ts'

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code === 'not_found') {
    return 'Không tìm thấy thông tin của con. Có thể đã bị xóa.'
  }
  return commonErrorMessage(error)
}
