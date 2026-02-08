import axios, { AxiosError } from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const http = axios.create({
  baseURL,
  timeout: 15000,
})

// 请求拦截：默认带 access_token
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise: Promise<string> | null = null

async function refreshAccessTokenOnce(): Promise<string> {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) throw new Error('No refresh token')

  // 用“裸 axios”请求 refresh，避免再次进入 http 拦截器（防止递归）
  const { data } = await axios.post(
    `${baseURL}/token/refresh`,
    null,
    { headers: { Authorization: `Bearer ${refreshToken}` } }
  )

  const newAccessToken = data?.access_token
  if (!newAccessToken) throw new Error('Refresh did not return access_token')

  localStorage.setItem('access_token', newAccessToken)
  return newAccessToken
}

http.interceptors.response.use(
  (resp) => resp,
  async (err: AxiosError) => {
    const status = err.response?.status
    const original = err.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined

    // 非 401：直接抛错
    if (status !== 401 || !original) throw err

    // 避免死循环：同一个请求只重试一次
    if (original._retry) throw err
    original._retry = true

    try {
      // 并发锁：同一时刻只 refresh 一次
      refreshPromise = refreshPromise ?? refreshAccessTokenOnce()
      const newToken = await refreshPromise
      refreshPromise = null

      // 更新原请求头并重试
      original.headers = original.headers ?? {}
      original.headers.Authorization = `Bearer ${newToken}`
      return http.request(original)
    } catch (e) {
      refreshPromise = null
      // refresh 失败才判定彻底未登录
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
      throw err
    }
  }
)
