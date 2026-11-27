import { ApiError } from '@/shared/api/client.ts'
import { commonErrorMessage } from '@/shared/api/errors.ts'
import type { DeviceAlert, DeviceAlertType } from '@/shared/types/alerts.ts'

const TYPE_LABELS: Record<DeviceAlertType, string> = {
  enforcement_disabled: 'Đã tắt cưỡng chế',
  clock_tampered: 'Đồng hồ bị chỉnh',
}

const DETAIL_LABELS: Record<string, string> = {
  tray_unavailable: 'Không bật được ứng dụng khay sau 3 lần thử.',
  backward: 'Đồng hồ máy bị chỉnh lùi so với giờ thật.',
  forward: 'Đồng hồ máy bị chỉnh tiến so với giờ thật.',
}

export function alertTypeLabel(type: string): string {
  return TYPE_LABELS[type as DeviceAlertType] ?? type
}

export function alertDetail(alert: Pick<DeviceAlert, 'detail'>): string | null {
  if (!alert.detail) return null
  return DETAIL_LABELS[alert.detail] ?? alert.detail
}

export function alertErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code === 'not_found') return 'Không tìm thấy thiết bị. Có thể đã bị gỡ.'
  return commonErrorMessage(error)
}
