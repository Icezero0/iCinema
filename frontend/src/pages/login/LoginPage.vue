<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import { useAuthStore } from "@/stores/auth.store";
import { useI18n } from "vue-i18n";
import { EyeIcon, EyeSlashIcon } from "@heroicons/vue/24/outline";
import LocaleMenuButton from "@/components/LocaleMenuButton.vue";
import { login } from "@/infra/api/auth.api";
import { getBackendErrorReason } from "@/infra/http/client";
import AppIcon from "@/ui/base/AppIcon.vue";
import BaseIconButton from "@/ui/base/BaseIconButton.vue";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const { t } = useI18n();

const email = ref("");
const password = ref("");
const passwordVisible = ref(false);

const isSubmitting = ref(false);
const errorMsg = ref("");

const showRegisteredHint = computed(() => route.query.registered === "1");

function setError(msg: string) {
  errorMsg.value = msg;
}

function extractErrorMessage(err: any) {
  if (getBackendErrorReason(err) === "invalid_credentials") {
    return t("auth.login.invalid");
  }
  const detail = err?.response?.data?.detail;

  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (typeof err?.message === "string" && err.message) return err.message;

  return t("auth.login.invalid");
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
    const r = await login(e, p);

    if (!r?.access_token || !r?.refresh_token) {
      throw new Error("Login failed: missing token pair.");
    }

    auth.setTokens(r.access_token, r.refresh_token);
    await auth.fetchMe();

    const redirect =
      typeof route.query.redirect === "string" ? route.query.redirect : "/";
    await router.replace(redirect);
  } catch (err: any) {
    setError(extractErrorMessage(err));
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

      <div class="passwordField">
        <BaseInput
          v-model="password"
          :type="passwordVisible ? 'text' : 'password'"
          autocomplete="current-password"
          :placeholder="t('auth.login.password')"
          :disabled="isSubmitting"
        />
        <BaseIconButton
          class="passwordToggle"
          :aria-label="t(passwordVisible ? 'auth.login.hidePassword' : 'auth.login.showPassword')"
          :aria-pressed="passwordVisible"
          :disabled="isSubmitting"
          @click="passwordVisible = !passwordVisible"
        >
          <Transition name="passwordIcon" mode="out-in">
            <AppIcon
              :key="passwordVisible ? 'visible' : 'hidden'"
              :icon="passwordVisible ? EyeSlashIcon : EyeIcon"
              :size="20"
            />
          </Transition>
        </BaseIconButton>
      </div>

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
        <RouterLink class="link" to="/auth/register">
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

.passwordField {
  position: relative;
}

.passwordField :deep(.inp) {
  box-sizing: border-box;
  width: 100%;
  padding-right: 48px;
}

.passwordField .passwordToggle {
  position: absolute;
  top: 50%;
  right: 3px;
  width: 34px;
  height: 34px;
  transform: translateY(-50%);
  border-radius: 50%;
  color: var(--c-text-muted);
}

.passwordToggle:focus-visible {
  outline: 2px solid var(--c-accent);
  outline-offset: -2px;
}

.passwordIcon-enter-active,
.passwordIcon-leave-active {
  transition: opacity 0.14s ease, transform 0.14s ease;
}

.passwordIcon-enter-from,
.passwordIcon-leave-to {
  opacity: 0;
  transform: scale(0.75);
}

@media (prefers-reduced-motion: reduce) {
  .passwordIcon-enter-active,
  .passwordIcon-leave-active {
    transition: none;
  }
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
