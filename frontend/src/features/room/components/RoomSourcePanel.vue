<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import {
  DocumentIcon,
  LinkIcon,
  QuestionMarkCircleIcon,
} from "@heroicons/vue/24/outline";
import AppIcon from "@/ui/base/AppIcon.vue";
import type { RoomVideoSourceType } from "@/infra/api/rooms.api";

const props = defineProps<{
  title: string;
  sourceType: RoomVideoSourceType;
  externalUrl: string;
  localFileName: string;
  localRoomTargetSet?: boolean;
  canSetLocalRoomTarget?: boolean;
  localSelectedAction?: "match_room_target" | "set_room_target" | null;
  message?: string;
  messageTone?: "muted" | "error";
  hashProgress?: number | null;
  applying?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:sourceType", value: RoomVideoSourceType): void;
  (e: "update:externalUrl", value: string): void;
  (e: "select-local-match-file", value: File | null): void;
  (e: "select-local-target-file", value: File | null): void;
  (e: "apply"): void;
}>();

const { t } = useI18n();

const matchFileInputRef = ref<HTMLInputElement | null>(null);
const targetFileInputRef = ref<HTMLInputElement | null>(null);
const targetHelpOpen = ref(false);
const videoUrlExtensions = [
  ".mp4",
  ".webm",
  ".ogg",
  ".ogv",
  ".mov",
  ".m4v",
  ".m3u8",
];
const supportedLocalFileTypes = [
  "video/mp4",
  "video/webm",
  "video/ogg",
  "video/quicktime",
  ".mp4",
  ".m4v",
  ".webm",
  ".ogg",
  ".ogv",
  ".mov",
].join(",");

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
  if (props.localSelectedAction === "match_room_target") {
    return props.localRoomTargetSet === true && props.localFileName.trim().length > 0;
  }
  if (props.localSelectedAction === "set_room_target") {
    return props.canSetLocalRoomTarget === true && props.localFileName.trim().length > 0;
  }
  return false;
});
const localModeOptions = computed(() => [
  {
    value: "match_room_target" as const,
    label: t("room.sourcePanel.matchRoomTarget"),
    disabled: props.localRoomTargetSet !== true,
  },
  {
    value: "set_room_target" as const,
    label: t("room.sourcePanel.setAsRoomTarget"),
    disabled: props.canSetLocalRoomTarget !== true,
  },
]);

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
const actionMessage = computed(() =>
  shouldShowExternalUrlError.value
    ? externalUrlError.value
    : props.message ?? "");
const actionMessageIsError = computed(() =>
  shouldShowExternalUrlError.value || props.messageTone === "error");
const shouldShowHashProgress = computed(() =>
  props.sourceType === "local_file" &&
  props.applying &&
  typeof props.hashProgress === "number");

function openMatchFilePicker() {
  if (!props.localRoomTargetSet) return;
  matchFileInputRef.value?.click();
}

function openTargetFilePicker() {
  if (!props.canSetLocalRoomTarget) return;
  targetFileInputRef.value?.click();
}

function onMatchFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  emit("select-local-match-file", target.files?.[0] ?? null);
  target.value = "";
}

function onTargetFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  emit("select-local-target-file", target.files?.[0] ?? null);
  target.value = "";
}

function toggleTargetHelp() {
  targetHelpOpen.value = !targetHelpOpen.value;
}

function closeTargetHelp() {
  targetHelpOpen.value = false;
}

function selectLocalMode(value: "match_room_target" | "set_room_target") {
  if (value === "match_room_target") {
    emit("select-local-match-file", null);
    return;
  }

  emit("select-local-target-file", null);
}
</script>

<template>
  <div class="sourcePanelContent" @click="closeTargetHelp">
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
        <div class="localFilePanel">
        <div class="localTargetHeader">
          <span class="localTargetLabel">{{ t("room.sourcePanel.localRoomTarget") }}</span>
          <span class="localTargetStatus" :class="{ active: localRoomTargetSet }">
            {{ localRoomTargetSet ? t("room.sourcePanel.localRoomTargetSet") : t("room.sourcePanel.localRoomTargetUnset") }}
          </span>
          <span class="localTargetHelpWrap">
            <button
              class="sourceHelpBtn"
              type="button"
              :aria-label="t('room.sourcePanel.localRoomTargetHelpLabel')"
              :aria-expanded="targetHelpOpen"
              @click.stop="toggleTargetHelp"
            >
              <AppIcon :icon="QuestionMarkCircleIcon" :size="20" />
            </button>
            <span v-if="targetHelpOpen" class="sourceHelpBubble" @click.stop>
              {{ t("room.sourcePanel.localRoomTargetHelp") }}
            </span>
          </span>
        </div>

        <div
          class="localModeList"
          role="radiogroup"
          :aria-label="t('room.sourcePanel.localModeLabel')"
        >
          <button
            v-for="option in localModeOptions"
            :key="option.value"
            class="localModeOption"
            type="button"
            role="radio"
            :aria-checked="localSelectedAction === option.value"
            :disabled="option.disabled"
            :class="{ active: localSelectedAction === option.value }"
            @click="selectLocalMode(option.value)"
          >
            <span class="localModeRadio" aria-hidden="true" />
            <span>{{ option.label }}</span>
          </button>
        </div>

        <div class="filePickerRow">
          <button
            class="chooseFileBtn"
            type="button"
            :disabled="!localSelectedAction"
            @click="localSelectedAction === 'match_room_target' ? openMatchFilePicker() : openTargetFilePicker()"
          >
            <AppIcon :icon="DocumentIcon" :size="15" />
            <span>{{ t("room.sourcePanel.chooseFile") }}</span>
          </button>
          <span class="fileName" :class="{ empty: !localFileName }">
            {{ localFileName || t("room.sourcePanel.noFileSelected") }}
          </span>
          <input
            ref="matchFileInputRef"
            class="hiddenFileInput"
            type="file"
            :accept="supportedLocalFileTypes"
            @change="onMatchFileChange"
          >
          <input
            ref="targetFileInputRef"
            class="hiddenFileInput"
            type="file"
            :accept="supportedLocalFileTypes"
            @change="onTargetFileChange"
          >
        </div>
      </div>
    </div>

    <div class="sourcePanelActions">
      <span class="actionMessage" :class="{ error: actionMessageIsError }">
        {{ actionMessage }}
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

    <div
      v-if="shouldShowHashProgress"
      class="hashProgress"
      role="progressbar"
      :aria-valuemin="0"
      :aria-valuemax="100"
      :aria-valuenow="Math.round(hashProgress ?? 0)"
    >
      <div class="hashProgressTrack">
        <span
          class="hashProgressFill"
          :style="{ width: `${Math.min(100, Math.max(0, hashProgress ?? 0))}%` }"
        />
      </div>
      <span class="hashProgressLabel">
        {{ t("room.sourcePanel.hashProgress", { percent: Math.round(hashProgress ?? 0) }) }}
      </span>
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

.sourceHelpBtn {
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--c-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    color 160ms ease;
}

.sourceHelpBtn:hover,
.sourceHelpBtn[aria-expanded="true"] {
  background: color-mix(in srgb, var(--c-hover) 84%, var(--c-surface));
  color: var(--c-text);
}

.sourceHelpBubble {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 6;
  width: min(280px, calc(100vw - 72px));
  padding: 10px 12px;
  border: 1px solid var(--c-border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--c-surface) 96%, var(--c-bg));
  color: var(--c-text-muted);
  box-shadow: 0 14px 32px rgb(0 0 0 / 0.14);
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-line;
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

.localFilePanel {
  display: grid;
  gap: 10px;
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--c-border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--c-surface) 70%, var(--c-bg));
}

.localTargetHeader {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
  min-width: 0;
}

.localTargetLabel {
  color: var(--c-text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.localTargetHelpWrap {
  position: relative;
  display: inline-flex;
  margin-left: auto;
}

.filePickerRow {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.localTargetStatus {
  min-width: 0;
  height: 24px;
  padding: 0 8px;
  border: 1px solid var(--c-border);
  border-radius: 999px;
  background: color-mix(in srgb, var(--c-surface) 72%, var(--c-bg));
  color: var(--c-text-muted);
  font-size: 11px;
  display: flex;
  align-items: center;
  white-space: nowrap;
}

.localTargetStatus.active {
  color: var(--c-text);
  border-color: color-mix(in srgb, var(--c-primary) 22%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 8%, var(--c-surface));
}

.localModeList {
  display: grid;
  gap: 6px;
}

.localModeOption {
  min-width: 0;
  min-height: 34px;
  border: 1px solid var(--c-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--c-surface) 74%, var(--c-bg));
  color: var(--c-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  padding: 0 10px;
  font-size: 12px;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    color 160ms ease,
    box-shadow 180ms ease;
}

.localModeOption:hover:not(:disabled) {
  background: color-mix(in srgb, var(--c-hover) 84%, var(--c-surface));
  border-color: color-mix(in srgb, var(--c-primary) 18%, var(--c-border));
  color: var(--c-text);
}

.localModeOption.active {
  border-color: color-mix(in srgb, var(--c-primary) 38%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 9%, var(--c-surface));
  color: var(--c-text);
  box-shadow: 0 6px 14px rgb(0 0 0 / 0.05);
}

.localModeOption:disabled {
  cursor: not-allowed;
  color: color-mix(in srgb, var(--c-text-muted) 62%, transparent);
}

.localModeRadio {
  width: 10px;
  height: 10px;
  box-sizing: border-box;
  border: 2px solid color-mix(in srgb, var(--c-text-muted) 58%, var(--c-border));
  border-radius: 999px;
  background: transparent;
  flex: 0 0 auto;
}

.localModeOption.active .localModeRadio {
  border-color: var(--c-primary);
  background: var(--c-primary);
  box-shadow: inset 0 0 0 2px var(--c-surface);
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

.chooseFileBtn.active {
  border-color: color-mix(in srgb, var(--c-primary) 42%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 12%, var(--c-surface));
}

.chooseFileBtn:hover {
  background: color-mix(in srgb, var(--c-hover) 84%, var(--c-surface));
  border-color: color-mix(in srgb, var(--c-primary) 20%, var(--c-border));
}

.chooseFileBtn:disabled {
  cursor: not-allowed;
  color: var(--c-text-muted);
  border-color: var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 72%, var(--c-bg));
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

.hashProgress {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.hashProgressTrack {
  position: relative;
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: color-mix(in srgb, var(--c-border) 78%, var(--c-bg));
}

.hashProgressFill {
  position: absolute;
  inset: 0 auto 0 0;
  min-width: 4px;
  border-radius: inherit;
  background: color-mix(in srgb, var(--c-primary) 72%, #62a5ff);
  transition: width 120ms ease;
}

.hashProgressLabel {
  color: var(--c-text-muted);
  font-size: 11px;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

</style>
