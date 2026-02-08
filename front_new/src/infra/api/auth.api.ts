import { http } from '@/infra/http/client'

export type LoginResponse = {
  access_token: string
  refresh_token: string
  token_type: 'bearer' | string
}

export type RefreshResponse = {
  access_token: string
  token_type: 'bearer' | string
}

export async function login(email: string, password: string) {
  const body = new URLSearchParams()
  body.set('email', email)
  body.set('password', password)

  const { data } = await http.post<LoginResponse>('/token', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export async function refreshAccessToken(refreshToken: string) {
  const { data } = await http.post<RefreshResponse>(
    '/token/refresh',
    null,
    { headers: { Authorization: `Bearer ${refreshToken}` } }
  )
  return data
}
