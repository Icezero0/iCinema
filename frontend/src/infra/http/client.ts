import axios, { AxiosError } from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'

import { API_BASE_URL, refreshAccessTokenOnce, expireAuthSession, sessionGeneration } from '@/infra/auth/session'

const baseURL = API_BASE_URL
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
  (config as InternalAxiosRequestConfig & { sessionGeneration: number }).sessionGeneration = sessionGeneration()
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers = config.headers ?? {}
    if (!config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

http.interceptors.response.use(
  (resp) => {
    if ((resp.config as InternalAxiosRequestConfig & { sessionGeneration: number }).sessionGeneration !== sessionGeneration()) {
      throw new axios.CanceledError('Session changed')
    }
    return resp
  },
  async (err: AxiosError) => {
    if (err.config && (err.config as InternalAxiosRequestConfig & { sessionGeneration: number }).sessionGeneration !== sessionGeneration()) {
      throw new axios.CanceledError('Session changed')
    }
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

    const generation = sessionGeneration()
    try {
      const newToken = await refreshAccessTokenOnce()

      original.headers = original.headers ?? {}
      original.headers.Authorization = `Bearer ${newToken}`

      return http.request(original)
    } catch {
      if (generation !== sessionGeneration()) throw new axios.CanceledError('Session changed')
      expireAuthSession()
      throw err
    }
  },
)
