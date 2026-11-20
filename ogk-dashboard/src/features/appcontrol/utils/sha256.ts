/*
 * The file is hashed in the browser and never uploaded; crypto.subtle only exists on HTTPS or localhost.
 */
export async function sha256File(file: File): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer())
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

export function canHash(): boolean {
  return typeof crypto !== 'undefined' && crypto.subtle !== undefined
}
