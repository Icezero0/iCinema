import { defineStore } from 'pinia'
import { getMe, type MeResponse } from '@/infra/api/users.api'
import { refreshAccessToken } from '@/infra/api/auth.api'

type AuthStatus = 'unknown' | 'authenticated' | 'anonymous'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem('access_token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    status: 'unknown' as AuthStatus,
    me: null as MeResponse | null,
  }),

  getters: {
    isLoggedIn: (s) => s.status === 'authenticated',
  },

  actions: {
    setTokens(accessToken: string, refreshToken?: string) {
      this.accessToken = accessToken
      localStorage.setItem('access_token', accessToken)

      if (refreshToken) {
        this.refreshToken = refreshToken
        localStorage.setItem('refresh_token', refreshToken)
      }
    },

    logout() {
      this.accessToken = ''
      this.refreshToken = ''
      this.me = null
      this.status = 'anonymous'
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    },

    async init() {
      // 无 token：直接匿名
      if (!this.accessToken) {
        this.status = 'anonymous'
        return
      }

      // 有 token：尝试确认
      try {
        this.me = await getMe()
        this.status = 'authenticated'
        return
      } catch (e) {
        // access token 无效：尝试 refresh
      }

      if (!this.refreshToken) {
        this.logout()
        return
      }

      try {
        const r = await refreshAccessToken(this.refreshToken)
        this.setTokens(r.access_token) // refresh 不会返回 refresh_token
        this.me = await getMe()
        this.status = 'authenticated'
      } catch {
        this.logout()
      }
    },
  },
})
