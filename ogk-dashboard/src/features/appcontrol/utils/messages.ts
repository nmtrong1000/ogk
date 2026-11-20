import { ApiError } from '@/shared/api/client.ts'
import { commonErrorMessage } from '@/shared/api/errors.ts'
import type { AppRuleAction } from '@/shared/types/policy.ts'

export const MAX_APP_RULES = 200
export const NAME_ERROR = 'Nhập tên tệp chạy, ví dụ game.exe, không có đường dẫn thư mục.'
export const SHA_ERROR = 'Mã SHA-256 gồm đúng 64 ký tự 0-9 và a-f, hoặc để trống.'
export const DUPLICATE_ERROR = 'Đã có luật cho ứng dụng này với cùng mã SHA-256.'
export const LIMIT_ERROR = `Mỗi con có tối đa ${MAX_APP_RULES} luật ứng dụng.`

export const ACTION_LABELS: Record<AppRuleAction, string> = {
  block: 'Chặn',
  allow: 'Cho phép',
}

export function appcontrolErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code === 'invalid_app_rules') {
    return 'Danh sách ứng dụng không hợp lệ, hãy tải lại trang rồi thử lại.'
  }
  return commonErrorMessage(error)
}
