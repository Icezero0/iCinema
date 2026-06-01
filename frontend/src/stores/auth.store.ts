import { defineStore } from 'pinia'
import { getMe, type UserMeResponse } from '@/infra/api/users.api'
import { refreshAccessToken } from '@/infra/api/auth.api'

type AuthStatus = 'unknown' | 'authenticated' | 'anonymous'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem('access_token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    status: 'unknown' as AuthStatus,
    me: null as UserMeResponse | null,
  }),

  getters: {
    isLoggedIn: (s) => s.status === 'authenticated',
    canManageFeedback: (s) =>
      Boolean(s.me?.site_permissions?.includes('view_all_feedback')),
  },

  actions: {
    setMe(me: UserMeResponse) {
      this.me = me
      this.status = 'authenticated'
    },

    setTokens(accessToken: string, refreshToken?: string) {
      this.accessToken = accessToken
      localStorage.setItem('access_token', accessToken)

      if (refreshToken !== undefined) {
        this.refreshToken = refreshToken
        if (refreshToken) {
          localStorage.setItem('refresh_token', refreshToken)
        } else {
          localStorage.removeItem('refresh_token')
        }
      }
    },

    syncTokensFromStorage() {
      this.accessToken = localStorage.getItem('access_token') || ''
      this.refreshToken = localStorage.getItem('refresh_token') || ''
    },

    clearTokens() {
      this.accessToken = ''
      this.refreshToken = ''
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    },

    logout() {
      this.clearTokens()
      this.me = null
      this.status = 'anonymous'
    },

    async fetchMe() {
      const me = await getMe()
      this.setMe(me)
      return me
    },

    async init() {
      this.syncTokensFromStorage()

      if (!this.accessToken && !this.refreshToken) {
        this.status = 'anonymous'
        return
      }

      if (this.accessToken) {
        try {
          await this.fetchMe()
          this.syncTokensFromStorage()
          return
        } catch {
          // 这里 fetchMe 失败时，client.ts 很可能已经尝试过自动 refresh
          // 下面只把 refresh_token 作为最终兜底
        }
      }

      if (this.refreshToken) {
        try {
          const r = await refreshAccessToken(this.refreshToken)
          this.setTokens(r.access_token, r.refresh_token)
          await this.fetchMe()
          return
        } catch {
          this.logout()
          return
        }
      }

      this.logout()
    },
  },
})
