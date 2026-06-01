import { http } from '@/infra/http/client'

export type UserResponse = {
  id: number
  email: string
  username: string | null
  auto_accept: boolean
  avatar_url: string | null
}

export type SiteRole = 'user' | 'admin'
export type SitePermission =
  | 'create_feedback'
  | 'view_own_feedback'
  | 'view_all_feedback'
  | 'update_feedback'
  | 'delete_feedback'

export type UserMeResponse = UserResponse & {
  site_role: SiteRole
  site_permissions: SitePermission[]
}

export type UserListResponse = {
  items: UserResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type UserPatchPayload = {
  username?: string | null
  password?: string | null
  auto_accept?: boolean | null
}

export type AvatarUploadResponse = {
  avatar_url: string | null
}

export async function getUserById(userId: number) {
  const { data } = await http.get<UserResponse>(`/users/${userId}`)
  return data
}

export async function getUsers(params?: {
  page?: number
  page_size?: number
  username?: string | null
  email?: string | null
}) {
  const { data } = await http.get<UserListResponse>('/users', {
    params,
  })
  return data
}

export async function getMe() {
  const { data } = await http.get<UserMeResponse>('/users/me')
  return data
}

export async function patchMe(payload: UserPatchPayload) {
  const { data } = await http.patch<UserMeResponse>('/users/me', payload)
  return data
}

export async function patchMyAvatar(file: File) {
  const form = new FormData()
  form.append('file', file)

  const { data } = await http.patch<AvatarUploadResponse>(
    '/users/me/avatar',
    form,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    },
  )

  return data
}
