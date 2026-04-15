<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import LocaleMenuButton from "@/components/LocaleMenuButton.vue";
import { register } from "@/infra/api/auth.api";

const router = useRouter();
const route = useRoute();
const { t } = useI18n();

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

function extractErrorMessage(err: any) {
  const detail = err?.response?.data?.detail;

  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (typeof err?.message === "string" && err.message) return err.message;

  return t("auth.register.failed");
}

async function submit() {
  if (isSubmitting.value) return;
  errorMsg.value = "";

  const e = email.value.trim();
  const u = username.value.trim();
  const p = password.value;
  const c = confirmPassword.value;

  if (!e || !u || !p || !c) {
    setError(t("auth.register.missing"));
    return;
  }

  if (p !== c) {
    setError(t("auth.register.passwordMismatch"));
    return;
  }

  isSubmitting.value = true;
  try {
    await register({
      email: e,
      username: u,
      password: p,
    });

    await router.replace({
      path: "/auth/login",
      query: { registered: "1", redirect: redirect.value },
    });
  } catch (err: any) {
    setError(extractErrorMessage(err));
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
