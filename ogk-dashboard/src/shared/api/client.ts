/*
 * A 401 on /api/auth/me, /login and /register is a normal result, not an expired session.
 * When the ogk_csrf cookie is missing, a GET is sent first because the server sets the cookie on any response.
 */
export class ApiError extends Error {
  status: number
  code: string
  body: Record<string, unknown> | null

  constructor(status: number, code: string, body: Record<string, unknown> | null = null) {
    super(code)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.body = body
  }
}

const CSRF_COOKIE = 'ogk_csrf'
const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
const NO_REDIRECT_ON_401 = new Set(['/api/auth/me', '/api/auth/login', '/api/auth/register'])

let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

function readCookie(name: string): string | null {
  for (const part of document.cookie.split(';')) {
    const [key, ...rest] = part.trim().split('=')
    if (key === name) return decodeURIComponent(rest.join('='))
  }
  return null
}

async function csrfToken(): Promise<string> {
  let token = readCookie(CSRF_COOKIE)
  if (!token) {
    await fetch('/api/health', { credentials: 'same-origin' }).catch(() => undefined)
    token = readCookie(CSRF_COOKIE)
  }
  return token ?? ''
}

export type ApiInit = Omit<RequestInit, 'body'> & { json?: unknown }

export async function apiFetch<T>(path: string, init: ApiInit = {}): Promise<T> {
  const { json, ...rest } = init
  const method = (rest.method ?? 'GET').toUpperCase()
  const headers = new Headers(rest.headers)
  headers.set('Accept', 'application/json')
  if (json !== undefined) headers.set('Content-Type', 'application/json')
  if (UNSAFE_METHODS.has(method)) headers.set('X-CSRF-Token', await csrfToken())

  let response: Response
  try {
    response = await fetch(path, {
      ...rest,
      method,
      headers,
      body: json === undefined ? undefined : JSON.stringify(json),
      credentials: 'same-origin',
    })
  } catch {
    throw new ApiError(0, 'network_error')
  }

  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && !NO_REDIRECT_ON_401.has(path)) onUnauthorized?.()
    const code = typeof body?.detail === 'string' ? body.detail : `http_${response.status}`
    throw new ApiError(response.status, code, body)
  }
  return body as T
}
