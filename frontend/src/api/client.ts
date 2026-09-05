/**
 * Typed fetch wrapper for the ForexMind AI backend. Three failure modes are
 * kept distinct on purpose - the Analyze view (Phase 2) needs to tell "the
 * backend is unreachable" apart from "the backend returned an error" apart
 * from "the backend returned something we don't understand," since each
 * implies a different message to the user.
 */

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export type ApiErrorKind = 'network' | 'http' | 'parse'

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status?: number
  readonly body?: string

  constructor(
    kind: ApiErrorKind,
    message: string,
    opts?: { status?: number; body?: string },
  ) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = opts?.status
    this.body = opts?.body
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST'
  body?: unknown
  signal?: AbortSignal
}

export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const url = `${API_BASE_URL}${path}`

  let response: Response
  try {
    response = await fetch(url, {
      method: options.method ?? 'GET',
      headers:
        options.body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    })
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === 'AbortError') {
      throw cause
    }
    throw new ApiError(
      'network',
      `Could not reach ForexMind AI at ${API_BASE_URL}. Is the backend running?`,
    )
  }

  const rawBody = await response.text()

  if (!response.ok) {
    let detail = rawBody
    try {
      const parsed: unknown = JSON.parse(rawBody)
      if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
        detail = String((parsed as { detail: unknown }).detail)
      }
    } catch {
      // rawBody wasn't JSON - use it verbatim as the detail.
    }
    throw new ApiError(
      'http',
      detail || `Request failed with status ${response.status}`,
      {
        status: response.status,
        body: rawBody,
      },
    )
  }

  try {
    return rawBody.length > 0 ? (JSON.parse(rawBody) as T) : (undefined as T)
  } catch {
    throw new ApiError(
      'parse',
      'The backend returned a response that could not be parsed.',
      {
        status: response.status,
        body: rawBody,
      },
    )
  }
}
