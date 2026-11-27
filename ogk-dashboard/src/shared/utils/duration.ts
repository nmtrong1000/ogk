export function formatDuration(seconds: number): string {
  const minutes = Math.floor(Math.max(0, seconds) / 60)
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (hours === 0) return `${rest} phút`
  if (rest === 0) return `${hours} giờ`
  return `${hours} giờ ${rest} phút`
}

export function formatHours(seconds: number): string {
  return `${(seconds / 3600).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} giờ`
}
