/*
 * Current year from the user's clock; used only to show age and bound the birth year input.
 */
export function currentYear(): number {
  return new Date().getFullYear()
}

export function ageFrom(birthYear: number): number {
  return currentYear() - birthYear
}
