import { http } from '@/infra/http/client'

export type WelcomeResponse = { message: string }

export async function getWelcome() {
  const { data } = await http.get<WelcomeResponse>('/')
  return data
}
