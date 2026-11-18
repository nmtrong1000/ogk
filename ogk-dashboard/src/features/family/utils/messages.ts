import { ApiError } from '../../../shared/api/client.ts'
import { commonErrorMessage } from '../../../shared/api/errors.ts'

export const MAX_NAME_LENGTH = 64
export const MIN_BIRTH_YEAR = 2000

export const NAME_ERROR = `Tên con dài từ 1 đến ${MAX_NAME_LENGTH} ký tự`

export const BIRTH_YEAR_ERROR = `Chọn năm sinh từ ${MIN_BIRTH_YEAR} đến năm nay`

/** Lỗi gắn vào ô nhập tương ứng; lỗi khác hiện ở thông báo chung. */
export function fieldError(error: unknown): { name?: string; birthYear?: string } {
  if (!(error instanceof ApiError)) return {}
  if (error.code === 'invalid_name') return { name: NAME_ERROR }
  if (error.code === 'invalid_birth_year') return { birthYear: BIRTH_YEAR_ERROR }
  return {}
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'invalid_name') return NAME_ERROR
    if (error.code === 'invalid_birth_year') return BIRTH_YEAR_ERROR
    if (error.code === 'not_found') return 'Không tìm thấy thông tin của con. Có thể đã bị xóa.'
  }
  return commonErrorMessage(error)
}
