import { ApiError } from '../../../shared/api/client.ts'
import { commonErrorMessage } from '../../../shared/api/errors.ts'

function formatTime(iso: unknown): string {
  if (typeof iso !== 'string') return ''
  return new Date(iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
}

export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return commonErrorMessage(error)
  switch (error.code) {
    case 'invalid_credentials':
      return 'Email hoặc mật khẩu không đúng'
    case 'account_locked':
      return `Tài khoản tạm khóa do nhập sai nhiều lần. Thử lại sau ${formatTime(error.body?.locked_until)} hoặc nhờ admin mở khóa.`
    case 'invalid_email':
      return 'Email không hợp lệ'
    case 'password_too_short':
      return 'Mật khẩu phải có ít nhất 10 ký tự'
    case 'password_too_long':
      return 'Mật khẩu dài tối đa 256 ký tự'
    case 'email_taken':
      return 'Email này đã có tài khoản'
    default:
      return commonErrorMessage(error)
  }
}
