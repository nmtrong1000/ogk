/** Năm hiện tại theo giờ máy người dùng; chỉ dùng để hiện tuổi và giới hạn ô năm sinh. */
export function currentYear(): number {
  return new Date().getFullYear()
}

export function ageFrom(birthYear: number): number {
  return currentYear() - birthYear
}
