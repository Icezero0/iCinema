import { http } from '@/infra/http/client'

export type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: 'bearer' | string
}

export type RegisterPayload = {
  email: string
  username?: string | null
  password: string
}

export async function login(email: string, password: string) {
  const { data } = await http.post<TokenResponse>('/auth/login', {
    email,
    password,
  })
  return data
}

export async function register(payload: RegisterPayload) {
  const { data } = await http.post('/auth/register', payload)
  return data
}

export async function refreshAccessToken(refreshToken: string) {
  const { data } = await http.post<TokenResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  })
  return data
}