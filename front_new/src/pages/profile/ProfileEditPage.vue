<script setup lang="ts">
import { computed, reactive, ref, watch, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth.store";
import { patchMe, patchMyAvatar } from "@/infra/api/users.api";
import { resolveMediaUrl } from "@/infra/media";

import BaseCard from "@/ui/base/BaseCard.vue";
import BaseButton from "@/ui/base/BaseButton.vue";
import BaseConfirmDialog from "@/ui/base/BaseConfirmDialog.vue";
import AvatarCropDialog from "@/ui/domain/avatar/AvatarCropDialog.vue";

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();

const me = computed(() => auth.me);

const avatarPath = computed(() => me.value?.avatar_url ?? "");
const avatarUrl = computed(() => resolveMediaUrl(avatarPath.value));

// 初始值（用来判断 dirty）
const initial = ref({
  username: me.value?.username ?? "",
  email: me.value?.email ?? "",
});

const form = reactive({
  username: initial.value.username,
  email: initial.value.email, // 只读展示，不参与提交
  newPassword: "",
  confirmNewPassword: "",
});

// 头像：预览 src + File（裁剪后生成，跟随 Save 提交）
const fileInputRef = ref<HTMLInputElement | null>(null);
const avatarPreviewSrc = ref<string>("");
const avatarFile = ref<File | null>(null);

// crop dialog
const cropOpen = ref(false);
const pickedFile = ref<File | null>(null);

// leave confirm dialog
const leaveDialogOpen = ref(false);

function revokeLocalAvatarPreview() {
  if (avatarPreviewSrc.value.startsWith("blob:")) {
    URL.revokeObjectURL(avatarPreviewSrc.value);
  }
}

watch(
  () => me.value,
  (v) => {
    initial.value.username = v?.username ?? "";
    initial.value.email = v?.email ?? "";
    form.username = initial.value.username;
    form.email = initial.value.email;

    // 不要在 me 更新时清掉用户正在本地预览的头像
    // avatarPreviewSrc / avatarFile 只在保存成功或重新选择时变更
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  revokeLocalAvatarPreview();
});

const isSubmitting = ref(false);
const errorMsg = ref<string | null>(null);
const successMsg = ref<string | null>(null);

// ---- password state ----
const passwordTouched = computed(
  () => !!form.newPassword || !!form.confirmNewPassword,
);

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
const isAvatarDirty = computed(() => !!avatarFile.value);
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

function onCropDone(file: File) {
  revokeLocalAvatarPreview();
  avatarFile.value = file;
  avatarPreviewSrc.value = URL.createObjectURL(file);
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
  if (!isDirty.value) {
    return;
  }

  isSubmitting.value = true;

  try {
    const profilePayload: {
      username?: string | null;
      password?: string | null;
    } = {};

    if (isUsernameDirty.value) {
      profilePayload.username = usernameTrimmed;
    }

    if (passwordTouched.value) {
      profilePayload.password = form.newPassword;
    }

    if (Object.keys(profilePayload).length > 0) {
      await patchMe(profilePayload);
    }

    if (avatarFile.value) {
      await patchMyAvatar(avatarFile.value);
    }

    await auth.fetchMe();

    initial.value.username = auth.me?.username ?? "";
    initial.value.email = auth.me?.email ?? "";
    form.username = initial.value.username;
    form.email = initial.value.email;
    form.newPassword = "";
    form.confirmNewPassword = "";

    revokeLocalAvatarPreview();
    avatarFile.value = null;
    avatarPreviewSrc.value = "";

    successMsg.value = t("profile.toast.saved");
  } catch (e: any) {
    errorMsg.value =
      e?.response?.data?.detail?.[0]?.msg ??
      e?.message ??
      t("profile.toast.saveFailed");
  } finally {
    isSubmitting.value = false;
  }
}

function onBack() {
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

const displayAvatarSrc = computed(() => avatarPreviewSrc.value || avatarUrl.value);
</script>

<template>
  <AppPageShell
    :title="t('profile.title')"
    :back-text="t('profile.cancel')"
    :max-width="760"
    back-behavior="emit"
    @back="onBack"
  >
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
      </div>
    </BaseCard>
  </AppPageShell>
</template>

<style scoped>
.card {
  width: min(720px, 100%);
  margin: 0 auto;
  padding: 28px 28px 22px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  border-radius: 16px;
  box-shadow: var(--shadow-lg, 0 10px 30px rgba(0, 0, 0, 0.06));
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
  justify-content: flex-end;
  gap: 12px;
}
</style>
