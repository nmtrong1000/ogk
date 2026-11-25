import { ApiError } from '@/shared/api/client.ts'
import { commonErrorMessage } from '@/shared/api/errors.ts'

export const MAX_QUOTA_MINUTES = 1440
export const QUOTA_ERROR = 'Thời gian phải từ 0 phút đến 24 giờ.'

export function screentimeErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'invalid_quota') return QUOTA_ERROR
    if (error.code === 'invalid_schedule') return 'Lịch tuần không hợp lệ, hãy tải lại trang rồi thử lại.'
    if (error.code === 'invalid_app_groups')
      return 'Nhóm ứng dụng hoặc ngân sách không hợp lệ. Hãy kiểm tra tên nhóm và ngân sách từ 0 đến 1440 phút.'
  }
  return commonErrorMessage(error)
}
