<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import { useAuthStore } from "@/stores/auth.store";
import { useI18n } from "vue-i18n";
import LocaleMenuButton from "@/components/LocaleMenuButton.vue";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const { t } = useI18n();

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const email = ref("");
const password = ref("");

const isSubmitting = ref(false);
const errorMsg = ref("");

const showRegisteredHint = computed(() => route.query.registered === "1");

function setError(msg: string) {
  errorMsg.value = msg;
}

async function loginRequest(payload: { email: string; password: string }) {
  // 后端是 OAuth2 Password flow：x-www-form-urlencoded
  const body = new URLSearchParams();
  body.set("email", payload.email);
  body.set("password", payload.password);

  const res = await fetch(`${apiBase}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  // 401 / 422 都统一到表单错误（不弹窗）
  if (!res.ok) {
    // 尽量解析后端 detail，但不做复杂联想
    let msg = t("auth.login.invalid");

    try {
      const data = await res.json();
      // FastAPI 常见：{ detail: "..." } 或 { detail: [{ msg: "..." }, ...] }
      const detail = (data as any)?.detail;
      if (typeof detail === "string") msg = detail;
      else if (Array.isArray(detail) && detail[0]?.msg) msg = detail[0].msg;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }

  return (await res.json()) as {
    access_token: string;
    refresh_token?: string;
    token_type?: string;
  };
}

async function submit() {
  if (isSubmitting.value) return;
  errorMsg.value = "";

  const e = email.value.trim();
  const p = password.value;

  if (!e || !p) {
    setError(t("auth.login.missing"));
    return;
  }

  isSubmitting.value = true;
  try {
    const r = await loginRequest({ email: e, password: p });

    if (!r?.access_token) {
      throw new Error("Login failed: missing access token.");
    }

    auth.setTokens(r.access_token, r.refresh_token);
    await auth.init();

    // 登录成功：优先回 redirect，其次回首页
    const redirect =
      typeof route.query.redirect === "string" ? route.query.redirect : "/";
    await router.replace(redirect);
  } catch (err: any) {
    setError(err?.message || t("auth.login.invalid"));
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <BaseCard class="loginCard">
    <header class="header">
      <div class="headerRow">
        <div>
          <h1 class="title">{{ t("auth.login.title") }}</h1>
          <p class="subtitle">{{ t("auth.login.subtitle") }}</p>
        </div>
        <LocaleMenuButton :size="20" />
      </div>
    </header>

    <p v-if="showRegisteredHint" class="hint" role="status">
      {{ t("auth.login.registeredHint") }}
    </p>

    <form class="form" @submit.prevent="submit">
      <BaseInput
        v-model="email"
        type="email"
        autocomplete="email"
        inputmode="email"
        :placeholder="t('auth.login.email')"
        :disabled="isSubmitting"
      />

      <BaseInput
        v-model="password"
        type="password"
        autocomplete="current-password"
        :placeholder="t('auth.login.password')"
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
        {{ isSubmitting ? t("auth.login.submitting") : t("auth.login.submit") }}
      </BaseButton>

      <p class="foot">
        <span class="muted">{{ t("auth.login.noAccount") }}</span>
        <RouterLink class="link" to="/register">
          {{ t("auth.login.createOne") }}
        </RouterLink>
      </p>
    </form>
  </BaseCard>
</template>

<style scoped>
.loginCard {
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

.loginCard::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  /* 顶部一条非常淡的高光 */
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.08),
    transparent 28%
  );
}

:global([data-theme="dark"]) .loginCard::before {
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

.hint {
  margin: 0 0 12px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--c-border);
  background: var(--c-bg);
  color: var(--c-text);
  font-size: 13px;
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
  /* 如果你 tokens 里有 danger，就用；没有也不强依赖 */
  color: var(--c-danger, var(--c-text));
}

/* 不假设 BaseButton 内部结构，只保证占满宽度 */
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
