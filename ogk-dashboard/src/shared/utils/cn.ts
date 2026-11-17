/** Ghép class, bỏ qua giá trị rỗng: cn('a', ok && 'b') */
export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}
