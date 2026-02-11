import { http } from '@/infra/http/client'

export type MeResponse = {
  id: number
  email: string
  username: string | null
  avatar_path: string | null
  created_at: string
  auto_accept: boolean
  rooms_owned?: any
  rooms_joined?: any
}

export type User = {
  id: number;
  email: string;
  username: string;
  avatar_path: string | null;
  created_at: string;
  auto_accept?: boolean;
};

export type UserListResponse = {
  items: User[];
  total: number;
};

export async function getUserById(userId: number) {
  const { data } = await http.get<UserListResponse>("/users", {
    params: { userid: userId },
  });
  return data.items?.[0] ?? null;
}

export async function getMe() {
  const { data } = await http.get<MeResponse>('/users/me')
  return data
}

export type UserUpdatePayload = {
  email: string
  username?: string | null
  password?: string | null
  avatar_base64?: string | null
  auto_accept?: boolean | null
}

export async function updateMe(payload: UserUpdatePayload) {
  const { data } = await http.put<MeResponse>('/users/me', payload)
  return data
}
