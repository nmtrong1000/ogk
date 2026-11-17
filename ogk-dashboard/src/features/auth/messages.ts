import { ApiError } from '../../shared/api/client.ts'

function formatTime(iso: unknown): string {
  if (typeof iso !== 'string') return ''
  return new Date(iso).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })
}

export function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Có lỗi xảy ra, vui lòng thử lại'
  switch (error.code) {
    case 'invalid_credentials':
      return 'Email hoặc mật khẩu không đúng'
    case 'account_locked':
      return `Tài khoản tạm khóa do nhập sai nhiều lần. Thử lại sau ${formatTime(error.body?.locked_until)} hoặc nhờ admin mở khóa.`
    case 'rate_limited':
      return 'Bạn thử quá nhiều lần. Vui lòng đợi một phút.'
    case 'invalid_email':
      return 'Email không hợp lệ'
    case 'password_too_short':
      return 'Mật khẩu phải có ít nhất 10 ký tự'
    case 'password_too_long':
      return 'Mật khẩu dài tối đa 256 ký tự'
    case 'email_taken':
      return 'Email này đã có tài khoản'
    case 'csrf_failed':
      return 'Phiên làm việc không hợp lệ, hãy tải lại trang'
    case 'forbidden':
      return 'Bạn không có quyền thực hiện thao tác này'
    case 'not_found':
      return 'Không tìm thấy'
    case 'network_error':
      return 'Không kết nối được server'
    default:
      return `Lỗi ${error.status}`
  }
}
