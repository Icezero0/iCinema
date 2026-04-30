import axios, { AxiosError } from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'

const API_ORIGIN = import.meta.env.VITE_API_ORIGIN ?? 'http://localhost:8000'
const API_PREFIX = import.meta.env.VITE_API_PREFIX ?? '/api/v1'

const baseURL = API_ORIGIN + API_PREFIX

export const http = axios.create({
  baseURL,
  timeout: 15000,
})

export type BackendErrorPayload = {
  code?: string
  reason?: string
  message?: string
  details?: unknown
}

type BackendErrorResponse = {
  error?: BackendErrorPayload
}

export type BackendAxiosError = AxiosError & {
  backendError?: BackendErrorPayload
  backendReason?: string
}

type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
}

function extractBackendErrorPayload(err: unknown): BackendErrorPayload | null {
  if (!axios.isAxiosError(err)) return null
  const data = err.response?.data as BackendErrorResponse | undefined
  return data?.error ?? null
}

function annotateBackendError(err: AxiosError) {
  const backendError = extractBackendErrorPayload(err)
  if (!backendError) return

  const annotated = err as BackendAxiosError
  annotated.backendError = backendError
  annotated.backendReason = backendError.reason
}

export function getBackendErrorReason(err: unknown) {
  if (axios.isAxiosError(err)) {
    return (err as BackendAxiosError).backendReason ?? extractBackendErrorPayload(err)?.reason ?? ""
  }

  return ""
}

export function getBackendErrorMessage(err: unknown) {
  if (axios.isAxiosError(err)) {
    const backendError = (err as BackendAxiosError).backendError ?? extractBackendErrorPayload(err)
    return backendError?.message || err.message
  }

  return err instanceof Error ? err.message : ""
}

function clearAuthStorage() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

function redirectToLogin() {
  const redirect = `${window.location.pathname}${window.location.search}${window.location.hash}`
  window.location.href = `/auth/login?redirect=${encodeURIComponent(redirect)}`
}

function isAuthRequest(url?: string) {
  if (!url) return false
  return (
    url.includes('/auth/login') ||
    url.includes('/auth/register') ||
    url.includes('/auth/refresh')
  )
}

// 请求拦截：默认带 access_token
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers = config.headers ?? {}
    if (!config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

let refreshPromise: Promise<string> | null = null

async function refreshAccessTokenOnce(): Promise<string> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) throw new Error('No refresh token')

  const { data } = await axios.post<TokenResponse>(
    `${baseURL}/auth/refresh`,
    {
      refresh_token: refreshToken,
    },
    {
      timeout: 15000,
    },
  )

  const newAccessToken = data?.access_token
  const newRefreshToken = data?.refresh_token

  if (!newAccessToken || !newRefreshToken) {
    throw new Error('Refresh did not return complete token pair')
  }

  localStorage.setItem('access_token', newAccessToken)
  localStorage.setItem('refresh_token', newRefreshToken)

  return newAccessToken
}

http.interceptors.response.use(
  (resp) => resp,
  async (err: AxiosError) => {
    annotateBackendError(err)

    const status = err.response?.status
    const original = err.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined

    if (status !== 401 || !original) {
      throw err
    }

    // auth 自身请求失败，不再尝试 refresh
    if (isAuthRequest(original.url)) {
      throw err
    }

    // 同一个请求只重试一次
    if (original._retry) {
      throw err
    }
    original._retry = true

    try {
      refreshPromise =
        refreshPromise ??
        refreshAccessTokenOnce().finally(() => {
          refreshPromise = null
        })

      const newToken = await refreshPromise

      original.headers = original.headers ?? {}
      original.headers.Authorization = `Bearer ${newToken}`

      return http.request(original)
    } catch {
      clearAuthStorage()
      redirectToLogin()
      throw err
    }
  },
)
