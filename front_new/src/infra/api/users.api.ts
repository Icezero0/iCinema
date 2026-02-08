import { http } from '@/infra/http/client'

export type MeResponse = {
  id: number
  email: string
  username: string | null
  avatar_path: string | null
  created_at: string
  auto_accept: boolean
  // rooms_owned / rooms_joined 你可以先用 any 或后面再精确建模
  rooms_owned?: any
  rooms_joined?: any
}

export async function getMe() {
  const { data } = await http.get<MeResponse>('/users/me')
  return data
}