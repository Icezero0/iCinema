<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import {
  DocumentIcon,
  LinkIcon,
} from "@heroicons/vue/24/outline";
import AppIcon from "@/ui/base/AppIcon.vue";
import type { RoomVideoSourceType } from "@/infra/api/rooms.api";

const props = defineProps<{
  title: string;
  sourceType: RoomVideoSourceType;
  externalUrl: string;
  localFileName: string;
  applying?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:sourceType", value: RoomVideoSourceType): void;
  (e: "update:externalUrl", value: string): void;
  (e: "select-local-file", value: File | null): void;
  (e: "apply"): void;
}>();

const { t } = useI18n();

const fileInputRef = ref<HTMLInputElement | null>(null);
const videoUrlExtensions = [
  ".mp4",
  ".webm",
  ".ogg",
  ".ogv",
  ".mov",
  ".m4v",
  ".mkv",
  ".avi",
  ".flv",
  ".ts",
  ".m3u8",
];

const sourceTypeOptions = computed(() => [
  {
    value: "external_url" as const,
    label: t("room.sourcePanel.externalUrl"),
    icon: LinkIcon,
  },
  {
    value: "local_file" as const,
    label: t("room.sourcePanel.localFile"),
    icon: DocumentIcon,
  },
]);

const canApply = computed(() => {
  if (props.applying) return false;
  if (props.sourceType === "external_url") {
    return externalUrlError.value === "";
  }
  return props.localFileName.trim().length > 0;
});

const externalUrlError = computed(() => {
  const value = props.externalUrl.trim();
  if (!value) return t("room.sourcePanel.externalUrlRequired");

  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    return t("room.sourcePanel.externalUrlInvalid");
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return t("room.sourcePanel.externalUrlInvalidProtocol");
  }

  const pathname = decodeURIComponent(parsed.pathname).toLowerCase();
  if (!videoUrlExtensions.some((extension) => pathname.endsWith(extension))) {
    return t("room.sourcePanel.externalUrlUnsupported");
  }

  return "";
});

const shouldShowExternalUrlError = computed(() =>
  props.sourceType === "external_url" &&
  props.externalUrl.trim().length > 0 &&
  externalUrlError.value !== "");

function openFilePicker() {
  fileInputRef.value?.click();
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  emit("select-local-file", target.files?.[0] ?? null);
}
</script>

<template>
  <div class="sourcePanelContent">
    <div class="sourcePanelTitle">{{ title }}</div>

    <div
      class="sourceTypeSwitch"
      role="radiogroup"
      :aria-label="t('room.sourcePanel.typeLabel')"
    >
      <button
        v-for="option in sourceTypeOptions"
        :key="option.value"
        class="sourceTypeOption"
        type="button"
        role="radio"
        :aria-checked="sourceType === option.value"
        :class="{ active: sourceType === option.value }"
        @click="emit('update:sourceType', option.value)"
      >
        <AppIcon :icon="option.icon" :size="15" />
        <span>{{ option.label }}</span>
      </button>
    </div>

    <div v-if="sourceType === 'external_url'" class="sourceModePanel">
      <label class="sourceField">
        <span class="urlInputWrap">
          <input
            class="sourceInput"
            type="url"
            :value="externalUrl"
            :aria-invalid="shouldShowExternalUrlError"
            :placeholder="t('room.sourcePanel.externalUrlPlaceholder')"
            @input="emit('update:externalUrl', ($event.target as HTMLInputElement).value)"
          >
        </span>
      </label>
    </div>

    <div v-else class="sourceModePanel">
      <div class="sourceField">
        <div class="filePickerRow">
          <button class="chooseFileBtn" type="button" @click="openFilePicker">
            <AppIcon :icon="DocumentIcon" :size="15" />
            <span>{{ t("room.sourcePanel.chooseFile") }}</span>
          </button>
          <span class="fileName" :class="{ empty: !localFileName }">
            {{ localFileName || t("room.sourcePanel.noFileSelected") }}
          </span>
        </div>
        <input
          ref="fileInputRef"
          class="hiddenFileInput"
          type="file"
          accept="video/*"
          @change="onFileChange"
        >
      </div>
    </div>

    <div class="sourcePanelActions">
      <span class="actionMessage" :class="{ error: shouldShowExternalUrlError }">
        {{ shouldShowExternalUrlError ? externalUrlError : "" }}
      </span>
      <button
        class="applySourceBtn"
        type="button"
        :disabled="!canApply"
        @click="emit('apply')"
      >
        <span>{{ applying ? t("room.sourcePanel.applying") : t("room.sourcePanel.apply") }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.sourcePanelContent {
  display: grid;
  gap: 10px;
}

.sourcePanelTitle {
  font-size: 12px;
  font-weight: 650;
  color: var(--c-text-muted);
}

.sourceTypeSwitch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  border: 1px solid var(--c-border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--c-bg) 70%, var(--c-surface));
}

.sourceTypeOption {
  min-width: 0;
  min-height: 30px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--c-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    color 160ms ease,
    box-shadow 180ms ease;
}

.sourceTypeOption:hover {
  background: color-mix(in srgb, var(--c-hover) 84%, var(--c-surface));
  color: var(--c-text);
}

.sourceTypeOption.active {
  background: var(--c-surface);
  color: var(--c-text);
  box-shadow: 0 6px 14px rgb(0 0 0 / 0.07);
}

.sourceModePanel {
  display: grid;
  align-items: center;
}

.sourceField {
  display: grid;
  gap: 0;
  min-width: 0;
}

.urlInputWrap {
  position: relative;
  min-width: 0;
}

.sourceInput {
  width: 100%;
  height: 34px;
  min-width: 0;
  box-sizing: border-box;
  border: 1px solid var(--c-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--c-surface) 82%, var(--c-bg));
  color: var(--c-text);
  font-size: 12px;
  padding: 0 10px;
  outline: none;
  transition:
    border-color 160ms ease,
    box-shadow 180ms ease,
    background-color 160ms ease;
}

.sourceInput::placeholder {
  color: color-mix(in srgb, var(--c-text-muted) 72%, transparent);
}

.sourceInput:focus {
  border-color: color-mix(in srgb, var(--c-primary) 48%, var(--c-border));
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-primary) 14%, transparent);
  background: var(--c-surface);
}

.sourceInput[aria-invalid="true"] {
  border-color: color-mix(in srgb, var(--c-danger) 58%, var(--c-border));
}

.sourceInput[aria-invalid="true"]:focus {
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-danger) 14%, transparent);
}

.filePickerRow {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.chooseFileBtn {
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--c-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--c-surface) 86%, var(--c-bg));
  color: var(--c-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease;
}

.chooseFileBtn:hover {
  background: color-mix(in srgb, var(--c-hover) 84%, var(--c-surface));
  border-color: color-mix(in srgb, var(--c-primary) 20%, var(--c-border));
}

.fileName {
  min-width: 0;
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--c-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--c-surface) 72%, var(--c-bg));
  color: var(--c-text);
  font-size: 12px;
  display: flex;
  align-items: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fileName.empty {
  color: var(--c-text-muted);
}

.hiddenFileInput {
  display: none;
}

.sourcePanelActions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 2px;
  min-height: 34px;
}

.actionMessage {
  min-width: 0;
  color: var(--c-text-muted);
  font-size: 11px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actionMessage.error {
  color: var(--c-danger);
}

.applySourceBtn {
  height: 34px;
  padding: 0 14px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 30%, var(--c-border));
  border-radius: 10px;
  background: color-mix(in srgb, var(--c-primary) 12%, var(--c-surface));
  color: var(--c-text);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    box-shadow 180ms ease;
}

.applySourceBtn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--c-primary) 16%, var(--c-surface));
  border-color: color-mix(in srgb, var(--c-primary) 42%, var(--c-border));
  box-shadow: 0 8px 16px rgb(0 0 0 / 0.05);
}

.applySourceBtn:active:not(:disabled) {
  box-shadow: 0 4px 10px rgb(0 0 0 / 0.06);
}

.applySourceBtn:disabled {
  cursor: not-allowed;
  border-color: var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 72%, var(--c-bg));
  color: var(--c-text-muted);
  box-shadow: none;
  opacity: 1;
}

</style>
