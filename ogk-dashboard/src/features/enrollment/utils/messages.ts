import { ApiError } from '@/shared/api/client.ts'
import { commonErrorMessage } from '@/shared/api/errors.ts'

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'consent_required') return 'Cần đồng ý giám sát trước khi tạo mã.'
    if (error.code === 'child_not_found') return 'Không tìm thấy con này. Có thể đã bị xóa.'
    if (error.code === 'not_found') return 'Không tìm thấy thiết bị. Có thể đã bị gỡ.'
  }
  return commonErrorMessage(error)
}
