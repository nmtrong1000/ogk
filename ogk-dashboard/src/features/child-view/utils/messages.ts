import { ApiError } from '@/shared/api/client.ts'

export const EXPIRED_TEXT = 'Đường dẫn này đã hết hạn. Em hãy mở lại từ biểu tượng OGK ở góc màn hình nhé.'

export function childViewErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'invalid_code' || error.code === 'not_authenticated') return EXPIRED_TEXT
    if (error.code === 'rate_limited') return 'Em thử nhiều lần quá. Đợi một phút rồi thử lại nhé.'
    if (error.code === 'network_error') return 'Chưa kết nối được. Em hãy thử lại sau nhé.'
  }
  return 'Có lỗi nhỏ. Em hãy thử lại sau nhé.'
}
