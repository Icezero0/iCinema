<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth.store";
import { updateMe } from "@/infra/api/users.api";

import BaseCard from "@/ui/base/BaseCard.vue";
import BaseButton from "@/ui/base/BaseButton.vue";
import BaseConfirmDialog from "@/ui/base/BaseConfirmDialog.vue";
import AvatarCropDialog from "@/ui/domain/avatar/AvatarCropDialog.vue";

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const me = computed(() => auth.me);

const avatarPath = computed(() => me.value?.avatar_path ?? "");
const avatarUrl = computed(() => {
  if (!avatarPath.value) return "";
  return avatarPath.value.startsWith("http")
    ? avatarPath.value
    : `${apiBase}${avatarPath.value}`;
});

// 初始值（用来判断 dirty）
const initial = ref({
  username: me.value?.username ?? "",
  email: me.value?.email ?? "",
});

const form = reactive({
  username: initial.value.username,
  email: initial.value.email, // UI 禁用，但提交必须带上
  newPassword: "",
  confirmNewPassword: "",
});

// 头像：预览 src + dataURL（裁剪后生成，跟随 Save 提交）
const fileInputRef = ref<HTMLInputElement | null>(null);
const avatarPreviewSrc = ref<string>(""); // dataURL（裁剪结果）优先；否则用 avatarUrl
const avatarDataUrl = ref<string | null>(null); // data:image/...;base64,...

// crop dialog
const cropOpen = ref(false);
const pickedFile = ref<File | null>(null);

// leave confirm dialog
const leaveDialogOpen = ref(false);

watch(
  () => me.value,
  (v) => {
    initial.value.username = v?.username ?? "";
    initial.value.email = v?.email ?? "";
    form.username = initial.value.username;
    form.email = initial.value.email;

    // 注意：不要在 me 更新时清掉用户正在裁剪/预览的本地头像
    // avatarPreviewSrc / avatarDataUrl 只在保存成功或用户重新选择时变更
  },
  { immediate: true },
);

const isSubmitting = ref(false);
const errorMsg = ref<string | null>(null);
const successMsg = ref<string | null>(null);

// ---- password state ----
const passwordTouched = computed(
  () => !!form.newPassword || !!form.confirmNewPassword,
);

// 只要确认框有输入，不一致就提示
const showConfirmMismatch = computed(() => {
  if (!form.confirmNewPassword) return false;
  return form.newPassword !== form.confirmNewPassword;
});

const passwordMismatch = computed(() => {
  if (!passwordTouched.value) return false;
  return form.newPassword !== form.confirmNewPassword;
});

// ---- dirty flags ----
const isUsernameDirty = computed(
  () => form.username !== initial.value.username,
);
const isAvatarDirty = computed(() => !!avatarDataUrl.value);
const isPasswordDirty = computed(() => passwordTouched.value);

const isDirty = computed(
  () => isUsernameDirty.value || isPasswordDirty.value || isAvatarDirty.value,
);

// label 星号（按字段级）
const usernameLabel = computed(() =>
  isUsernameDirty.value ? `${t("profile.username")}*` : t("profile.username"),
);
const newPasswordLabel = computed(() =>
  isPasswordDirty.value
    ? `${t("profile.newPassword")}*`
    : t("profile.newPassword"),
);
const confirmPasswordLabel = computed(() =>
  isPasswordDirty.value
    ? `${t("profile.confirmNewPassword")}*`
    : t("profile.confirmNewPassword"),
);
const avatarHintLabel = computed(() =>
  isAvatarDirty.value ? `${t("profile.avatarHint")}*` : t("profile.avatarHint"),
);

function openFilePicker() {
  fileInputRef.value?.click();
}

function onPickAvatar(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  errorMsg.value = null;
  successMsg.value = null;

  pickedFile.value = file;
  cropOpen.value = true;

  // 允许重复选择同一文件
  input.value = "";
}

function onCropDone(dataUrl: string) {
  // 裁剪结果：dataURL（带 data:image 头部）
  avatarPreviewSrc.value = dataUrl;
  avatarDataUrl.value = dataUrl;

  // 清理 pickedFile（可选）
  pickedFile.value = null;
}

function onCropCancel() {
  pickedFile.value = null;
}

async function onSave() {
  errorMsg.value = null;
  successMsg.value = null;

  const usernameTrimmed = form.username.trim();
  if (!usernameTrimmed) {
    errorMsg.value = t("profile.errors.usernameRequired");
    return;
  }
  if (passwordMismatch.value) {
    errorMsg.value = t("profile.errors.passwordMismatch");
    return;
  }

  // OpenAPI: email 必填（即使 UI 禁用也必须带上）
  const emailValue = form.email || initial.value.email;
  if (!emailValue) {
    errorMsg.value = t("profile.errors.emailMissing");
    return;
  }

  isSubmitting.value = true;
  try {
    const payload: any = {
      email: emailValue,
      username: usernameTrimmed,
    };

    if (passwordTouched.value) payload.password = form.newPassword;
    if (avatarDataUrl.value) payload.avatar_base64 = avatarDataUrl.value;

    const updated = await updateMe(payload);
    auth.setMe(updated);

    // 同步本页状态（避免 dirty 一直为 true）
    initial.value.username = updated.username ?? "";
    initial.value.email = updated.email ?? "";
    form.username = initial.value.username;
    form.email = initial.value.email;
    form.newPassword = "";
    form.confirmNewPassword = "";

    // 保存成功：清掉本地裁剪结果，后续展示走后端 avatarUrl（更一致）
    avatarDataUrl.value = null;
    avatarPreviewSrc.value = "";

    successMsg.value = t("profile.toast.saved");
  } catch (e: any) {
    errorMsg.value = e?.message ?? t("profile.toast.saveFailed");
  } finally {
    isSubmitting.value = false;
  }
}

function onCancel() {
  if (isSubmitting.value) return;

  if (isDirty.value) {
    leaveDialogOpen.value = true;
    return;
  }

  router.push("/");
}

function confirmLeave() {
  router.push("/");
}

// 页面展示用：本地裁剪预览优先，其次后端 url
const displayAvatarSrc = computed(() => avatarPreviewSrc.value || avatarUrl.value);
</script>

<template>
  <div class="page">
    <!-- Unsaved confirm -->
    <BaseConfirmDialog
      v-model="leaveDialogOpen"
      :title="t('profile.unsaved.title')"
      :message="t('profile.unsaved.message')"
      :cancelText="t('profile.unsaved.stay')"
      :confirmText="t('profile.unsaved.leave')"
      variant="danger"
      @confirm="confirmLeave"
    />

    <!-- Crop dialog -->
    <AvatarCropDialog
      v-model="cropOpen"
      :file="pickedFile"
      :title="t('profile.crop.title')"
      @done="onCropDone"
      @cancel="onCropCancel"
    />

    <BaseCard class="card">
      <h1 class="title">{{ t("profile.title") }}</h1>

      <div class="avatarBlock">
        <button type="button" class="avatarButton" @click="openFilePicker">
          <img
            v-if="displayAvatarSrc"
            class="avatarImg"
            :src="displayAvatarSrc"
            alt="avatar"
          />
          <div v-else class="avatarPlaceholder" aria-hidden="true" />
        </button>

        <div class="avatarHint">{{ avatarHintLabel }}</div>

        <input
          ref="fileInputRef"
          type="file"
          accept="image/*"
          class="fileInput"
          @change="onPickAvatar"
        />
      </div>

      <div class="form">
        <label class="field">
          <div class="label">{{ usernameLabel }}</div>
          <input
            v-model="form.username"
            class="input"
            autocomplete="username"
          />
        </label>

        <label class="field">
          <div class="label">{{ t("profile.email") }}</div>
          <input :value="form.email" class="input" disabled />
          <div class="hint">{{ t("profile.emailReadonlyHint") }}</div>
        </label>

        <label class="field">
          <div class="label">{{ newPasswordLabel }}</div>
          <input
            v-model="form.newPassword"
            class="input"
            type="password"
            autocomplete="new-password"
            :placeholder="t('profile.noChange')"
          />
        </label>

        <label class="field">
          <div class="label">{{ confirmPasswordLabel }}</div>
          <input
            v-model="form.confirmNewPassword"
            class="input"
            type="password"
            autocomplete="new-password"
            :placeholder="t('profile.noChange')"
          />
          <div v-if="showConfirmMismatch" class="fieldError">
            {{ t("profile.errors.passwordMismatch") }}
          </div>
        </label>

        <p v-if="errorMsg" class="msg msgError">{{ errorMsg }}</p>
        <p v-else-if="successMsg" class="msg msgSuccess">{{ successMsg }}</p>
      </div>

      <div class="actions">
        <BaseButton
          type="button"
          variant="primary"
          :disabled="!isDirty || isSubmitting || passwordMismatch"
          :loading="isSubmitting"
          @click="onSave"
        >
          {{ t("profile.save") }}
        </BaseButton>

        <BaseButton
          type="button"
          variant="default"
          :disabled="isSubmitting"
          @click="onCancel"
        >
          {{ t("profile.cancel") }}
        </BaseButton>
      </div>
    </BaseCard>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: 32px 16px;
  background: var(--c-bg);
  color: var(--c-text);
}

.card {
  width: min(720px, 100%);
  padding: 28px 28px 22px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  border-radius: 16px;
  box-shadow: var(--shadow-lg, 0 10px 30px rgba(0, 0, 0, 0.06));
}

.title {
  text-align: center;
  margin: 0 0 18px;
  font-size: 20px;
  letter-spacing: 0.02em;
}

.avatarBlock {
  display: grid;
  place-items: center;
  gap: 10px;
  margin: 8px 0 18px;
}

.avatarButton {
  width: 256px;
  height: 256px;
  border-radius: 14px;
  border: 1px solid var(--c-border);
  background: transparent;
  padding: 0;
  cursor: pointer;
  overflow: hidden;

  position: relative;

  transform: translate3d(0, 0, 0) scale(1);
  will-change: transform, filter;
  backface-visibility: hidden;

  transition:
    transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1),
    filter 240ms cubic-bezier(0.2, 0.8, 0.2, 1);
}

.avatarButton::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(
    to bottom,
    rgb(255 255 255 / 0.08),
    rgb(255 255 255 / 0)
  );
  opacity: 0;
  transition: opacity 240ms ease;
}

.avatarButton::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: var(--c-hover);
  opacity: 0;
  transition: opacity 240ms ease;
}

.avatarButton:hover {
  transform: translate3d(0, -0.75px, 0) scale(1.01);
  filter: drop-shadow(0 10px 22px rgb(0 0 0 / 0.14));
}

.avatarButton:hover::before {
  opacity: 1;
}

.avatarButton:hover::after {
  opacity: 1;
}

.avatarImg {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transform: translateZ(0);
  backface-visibility: hidden;
}

.avatarPlaceholder {
  width: 100%;
  height: 100%;
  background: var(--c-hover);
}

.avatarHint {
  font-size: 12px;
  color: var(--c-text-muted);
}

.fileInput {
  display: none;
}

.form {
  display: grid;
  gap: 14px;
  margin-top: 6px;
}

.field {
  display: grid;
  gap: 8px;
}

.label {
  font-size: 13px;
  color: var(--c-text);
  opacity: 0.9;
}

.hint {
  margin-top: -2px;
  font-size: 12px;
  color: var(--c-text-muted);
}

.fieldError {
  margin-top: -2px;
  font-size: 12px;
  color: var(--c-danger);
}

.input {
  height: 40px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 70%, var(--c-bg));
  color: var(--c-text);
  outline: none;
  transition:
    border-color 120ms ease,
    background 120ms ease;
}
.input:focus {
  border-color: var(--c-primary);
}
.input:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.msg {
  margin: 2px 0 0;
  font-size: 13px;
}
.msgError {
  color: var(--c-danger);
}
.msgSuccess {
  color: var(--c-text);
  opacity: 0.9;
}

.actions {
  margin-top: 18px;
  display: flex;
  justify-content: center;
  gap: 12px;
}
</style>
