<script setup lang="ts">
import { useAuthStore } from '@/stores/auth.store'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <BaseLayout title="Home">
    <BaseCard>
      <p style="margin-top:0;">User: <b>{{ auth.me?.username ?? '-' }}</b></p>

      <div style="display:flex; gap: var(--s-2);">
        <BaseButton @click="logout">Logout</BaseButton>
      </div>
    </BaseCard>
  </BaseLayout>
</template>