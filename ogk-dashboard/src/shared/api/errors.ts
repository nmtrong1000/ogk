/*
 * FastAPI 422 responses have an array detail, so their code is http_422.
 */
import { ApiError } from './client.ts'

export function commonErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Có lỗi xảy ra, vui lòng thử lại'
  switch (error.code) {
    case 'not_authenticated':
      return 'Phiên đăng nhập đã hết, vui lòng đăng nhập lại'
    case 'forbidden':
      return 'Bạn không có quyền thực hiện thao tác này'
    case 'not_found':
      return 'Không tìm thấy'
    case 'csrf_failed':
      return 'Phiên làm việc không hợp lệ, hãy tải lại trang'
    case 'rate_limited':
      return 'Bạn thử quá nhiều lần. Vui lòng đợi một phút.'
    case 'network_error':
      return 'Không kết nối được server'
  }
  if (error.status === 422) return 'Dữ liệu nhập chưa hợp lệ'
  if (error.status >= 500) return 'Server đang gặp lỗi, vui lòng thử lại sau'
  return `Lỗi ${error.status}`
}
