<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import LocaleMenuButton from "@/components/LocaleMenuButton.vue";

const router = useRouter();
const route = useRoute();
const { t } = useI18n();

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const email = ref("");
const username = ref("");
const password = ref("");
const confirmPassword = ref("");

const isSubmitting = ref(false);
const errorMsg = ref("");

const redirect = computed(() =>
  typeof route.query.redirect === "string" ? route.query.redirect : "/",
);

function setError(msg: string) {
  errorMsg.value = msg;
}

async function registerRequest(payload: {
  email: string;
  username: string;
  password: string;
}) {
  const res = await fetch(`${apiBase}/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let msg = t("auth.register.failed");
    try {
      const data = await res.json();
      const detail = (data as any)?.detail;
      if (typeof detail === "string") msg = detail;
      else if (Array.isArray(detail) && detail[0]?.msg) msg = detail[0].msg;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }

  // 成功返回 User（但注册页通常不直接登录）
  return await res.json();
}

async function submit() {
  if (isSubmitting.value) return;
  errorMsg.value = "";

  const e = email.value.trim();
  const u = username.value.trim();
  const p = password.value;

  if (!e || !u || !p || !confirmPassword.value) {
    setError(t("auth.register.missing"));
    return;
  }

  if (p !== confirmPassword.value) {
    setError(t("auth.register.passwordMismatch"));
    return;
  }

  isSubmitting.value = true;
  try {
    await registerRequest({ email: e, username: u, password: p });

    // 注册成功：回登录页，带上 registered=1（你 login 页已支持提示）
    await router.replace({
      path: "/auth/login",
      query: { registered: "1", redirect: redirect.value },
    });
  } catch (err: any) {
    setError(err?.message || t("auth.register.failed"));
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <BaseCard class="registerCard">
    <header class="header">
      <div class="headerRow">
        <div>
          <h1 class="title">{{ t("auth.register.title") }}</h1>
        </div>
        <LocaleMenuButton :size="20" />
      </div>
    </header>

    <form class="form" @submit.prevent="submit">
      <BaseInput
        v-model="email"
        type="email"
        autocomplete="email"
        inputmode="email"
        :placeholder="t('auth.register.email')"
        :disabled="isSubmitting"
      />

      <BaseInput
        v-model="username"
        type="text"
        autocomplete="username"
        :placeholder="t('auth.register.username')"
        :disabled="isSubmitting"
      />

      <BaseInput
        v-model="password"
        type="password"
        autocomplete="new-password"
        :placeholder="t('auth.register.password')"
        :disabled="isSubmitting"
      />

      <BaseInput
        v-model="confirmPassword"
        type="password"
        autocomplete="new-password"
        :placeholder="t('auth.register.confirmPassword')"
        :disabled="isSubmitting"
      />

      <p v-if="errorMsg" class="error" role="alert">
        {{ errorMsg }}
      </p>

      <BaseButton
        class="primaryBtn"
        type="submit"
        variant="primary"
        :disabled="isSubmitting"
      >
        {{
          isSubmitting
            ? t("auth.register.submitting")
            : t("auth.register.submit")
        }}
      </BaseButton>

      <p class="foot">
        <span class="muted">{{ t("auth.register.haveAccount") }}</span>
        <RouterLink
          class="link"
          :to="{ path: '/auth/login', query: { redirect } }"
        >
          {{ t("auth.register.signIn") }}
        </RouterLink>
      </p>
    </form>
  </BaseCard>
</template>

<style scoped>
.registerCard {
  width: min(420px, 92vw);
  padding: 22px;
  border-radius: 16px;

  background: var(--c-surface);
  border: 1px solid color-mix(in oklab, var(--c-border) 80%, transparent);

  box-shadow:
    0 18px 50px rgba(0, 0, 0, 0.1),
    0 2px 10px rgba(0, 0, 0, 0.06);

  position: relative;
  overflow: hidden;
}

.registerCard::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.08),
    transparent 28%
  );
}

:global([data-theme="dark"]) .registerCard::before {
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.06),
    transparent 28%
  );
}

.headerRow {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.title {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
  font-weight: 650;
  color: var(--c-text);
  letter-spacing: -0.01em;
}

.subtitle {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--c-text-muted);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 10px;
}

.error {
  margin: 2px 0 0;
  font-size: 13px;
  color: var(--c-danger, var(--c-text));
}

.primaryBtn {
  margin-top: 6px;
}
.primaryBtn :deep(button),
.primaryBtn:deep(button) {
  width: 100%;
}

.foot {
  margin: 6px 0 0;
  font-size: 13px;
  display: flex;
  gap: 8px;
  align-items: center;
}

.muted {
  color: var(--c-text-muted);
}

.link {
  color: var(--c-text);
  text-decoration: none;
  border-bottom: 1px solid var(--c-border);
}
.link:hover {
  border-bottom-color: var(--c-text-muted);
}
</style>
