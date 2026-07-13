<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import type {
  RoomActiveSyncPermission,
  RoomJoinAuditMode,
  RoomSyncPolicy,
  RoomVisibility,
} from "@/infra/api/rooms.api";

defineProps<{
  roomName: string;
  visibility: RoomVisibility;
  joinAuditMode: RoomJoinAuditMode;
  syncPolicy: RoomSyncPolicy;
  activeSyncPermission: RoomActiveSyncPermission;
  seekAutoPause: boolean;
  settingsLoading?: boolean;
  settingsError?: string;
  canManageRoomSettings?: boolean;
  isOwner?: boolean;
  localSyncStrategy: string;
  localSyncOptions: { value: string; label: string }[];
  danmakuEnabled: boolean;
  danmakuOpacity: number;
  danmakuSpeed: number;
}>();

const emit = defineEmits<{
  (e: "update:roomName", value: string): void;
  (e: "update:visibility", value: RoomVisibility): void;
  (e: "update:joinAuditMode", value: RoomJoinAuditMode): void;
  (e: "update:syncPolicy", value: RoomSyncPolicy): void;
  (e: "update:activeSyncPermission", value: RoomActiveSyncPermission): void;
  (e: "update:seekAutoPause", value: boolean): void;
  (e: "update:localSyncStrategy", value: string): void;
  (e: "update:danmakuEnabled", value: boolean): void;
  (e: "update:danmakuOpacity", value: number): void;
  (e: "update:danmakuSpeed", value: number): void;
}>();

const { t } = useI18n();

const visibilityOptions = computed(() => [
  { value: "public", label: t("room.settings.visibilityPublic") },
  { value: "private", label: t("room.settings.visibilityPrivate") },
]);
const joinAuditOptions = computed(() => [
  { value: "manual_review", label: t("room.settings.auditManual") },
  { value: "auto_approve", label: t("room.settings.auditAutoApprove") },
  { value: "auto_reject", label: t("room.settings.auditAutoReject") },
]);
const syncPolicyOptions = computed(() => [
  { value: "auto_sync", label: t("room.settings.syncAuto") },
  { value: "disabled", label: t("room.settings.syncManual") },
]);
const activeSyncPermissionOptions = computed(() => [
  { value: "owner_only", label: t("room.settings.activeSyncOwnerOnly") },
  { value: "owner_and_manager", label: t("room.settings.activeSyncOwnerAndManager") },
  { value: "all_members", label: t("room.settings.activeSyncAllMembers") },
]);

function handleSeekAutoPauseChange(event: Event) {
  emit("update:seekAutoPause", (event.target as HTMLInputElement).checked);
}

function handleDanmakuEnabledChange(event: Event) {
  emit("update:danmakuEnabled", (event.target as HTMLInputElement).checked);
}

function handleDanmakuOpacityChange(event: Event) {
  emit("update:danmakuOpacity", Number((event.target as HTMLInputElement).value));
}

function handleDanmakuSpeedChange(event: Event) {
  emit("update:danmakuSpeed", Number((event.target as HTMLInputElement).value));
}
</script>

<template>
  <div class="settingsStack">
    <section class="settingsSection">
      <div class="sectionTitle">{{ t("room.settings.infoSection") }}</div>

      <label class="settingField">
        <span class="settingLabel">{{ t("room.settings.roomName") }}</span>
        <BaseInput
          v-if="canManageRoomSettings"
          :model-value="roomName"
          @update:model-value="emit('update:roomName', $event)"
        />
        <span v-else class="readonlyValue">{{ roomName }}</span>
      </label>

      <label class="settingField">
        <span class="settingLabel">{{ t("room.settings.visibility") }}</span>
        <BaseSelect
          v-if="canManageRoomSettings"
          :model-value="visibility"
          :options="visibilityOptions"
          @update:model-value="emit('update:visibility', $event as RoomVisibility)"
        />
        <span v-else class="readonlyValue">
          {{ visibility === "public" ? t("room.settings.visibilityPublic") : t("room.settings.visibilityPrivate") }}
        </span>
      </label>
    </section>

    <section v-if="canManageRoomSettings" class="settingsSection">
      <div class="sectionHeader">
        <div class="sectionTitle">{{ t("room.settings.policySection") }}</div>
        <div v-if="settingsLoading" class="sectionState">{{ t("common.loading") }}</div>
        <div v-else-if="settingsError" class="sectionState error">{{ settingsError }}</div>
      </div>

      <label class="settingField">
        <span class="settingLabel">{{ t("room.settings.joinAuditMode") }}</span>
        <BaseSelect
          :model-value="joinAuditMode"
          :options="joinAuditOptions"
          @update:model-value="emit('update:joinAuditMode', $event as RoomJoinAuditMode)"
        />
      </label>

      <label class="settingField">
        <span class="settingLabel">{{ t("room.settings.roomSyncPolicy") }}</span>
        <BaseSelect
          :model-value="syncPolicy"
          :options="syncPolicyOptions"
          :disabled="settingsLoading"
          @update:model-value="emit('update:syncPolicy', $event as RoomSyncPolicy)"
        />
      </label>

      <label v-if="isOwner" class="settingField">
        <span class="settingLabel">{{ t("room.settings.activeSyncPermission") }}</span>
        <BaseSelect
          :model-value="activeSyncPermission"
          :options="activeSyncPermissionOptions"
          :disabled="settingsLoading"
          @update:model-value="emit('update:activeSyncPermission', $event as RoomActiveSyncPermission)"
        />
      </label>

      <label class="settingField checkboxField">
        <span class="settingLabel">{{ t("room.settings.seekAutoPause") }}</span>
        <span class="checkboxControl">
          <input
            class="checkboxInput"
            type="checkbox"
            :checked="seekAutoPause"
            :disabled="settingsLoading"
            @change="handleSeekAutoPauseChange"
          />
          <span class="checkboxVisual" aria-hidden="true" />
        </span>
      </label>
    </section>

    <section class="settingsSection">
      <div class="sectionTitle">{{ t("room.settings.danmakuSection") }}</div>

      <label class="settingField checkboxField">
        <span class="settingLabel">{{ t("room.settings.danmakuEnabled") }}</span>
        <span class="checkboxControl">
          <input
            class="checkboxInput"
            type="checkbox"
            :checked="danmakuEnabled"
            @change="handleDanmakuEnabledChange"
          />
          <span class="checkboxVisual" aria-hidden="true" />
        </span>
      </label>

      <label class="settingField rangeField">
        <span class="settingLabel">{{ t("room.settings.danmakuOpacity") }}</span>
        <span class="rangeControl">
          <input
            class="rangeInput"
            type="range"
            min="0.35"
            max="1"
            step="0.05"
            :value="danmakuOpacity"
            @input="handleDanmakuOpacityChange"
          />
          <span class="rangeValue">{{ Math.round(danmakuOpacity * 100) }}%</span>
        </span>
      </label>

      <label class="settingField rangeField">
        <span class="settingLabel">{{ t("room.settings.danmakuSpeed") }}</span>
        <span class="rangeControl">
          <input
            class="rangeInput"
            type="range"
            min="0.5"
            max="2"
            step="0.1"
            :value="danmakuSpeed"
            @input="handleDanmakuSpeedChange"
          />
          <span class="rangeValue">{{ danmakuSpeed.toFixed(1) }}x</span>
        </span>
      </label>
    </section>

  </div>
</template>

<style scoped>
.settingsStack {
  display: grid;
  gap: 12px;
}

.settingsSection {
  padding: 12px;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--c-surface) 76%, var(--c-bg));
  display: grid;
  gap: 12px;
}

.sectionTitle {
  font-size: 13px;
  font-weight: 650;
  color: var(--c-text);
}

.sectionHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
}

.sectionState {
  min-width: 0;
  color: var(--c-text-muted);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sectionState.error {
  color: var(--c-danger);
}

.settingField {
  display: grid;
  grid-template-columns: minmax(72px, 0.8fr) minmax(0, 1.4fr);
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.settingLabel {
  font-size: 12px;
  color: var(--c-text-muted);
  line-height: 1.25;
}

.settingField :deep(.inp),
.settingField :deep(.trigger) {
  min-height: 34px;
  height: 34px;
  border-radius: 10px;
  font-size: 12px;
}

.settingField :deep(.inp) {
  padding: 0 10px;
}

.settingField :deep(.trigger) {
  padding: 0 10px;
}

.settingField :deep(.triggerLabel) {
  font-size: 12px;
}

.settingField :deep(.fieldRoot) {
  gap: 5px;
}

.checkboxField {
  min-height: 34px;
}

.checkboxControl {
  position: relative;
  justify-self: start;
  width: 42px;
  height: 24px;
  display: inline-flex;
  align-items: center;
}

.checkboxInput {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.checkboxInput:disabled {
  cursor: not-allowed;
}

.checkboxVisual {
  width: 42px;
  height: 24px;
  border-radius: 999px;
  border: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 72%, var(--c-bg));
  box-shadow: inset 0 1px 2px rgb(15 23 42 / 0.08);
  pointer-events: none;
  transition:
    background-color 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.checkboxVisual::after {
  content: "";
  position: absolute;
  top: 4px;
  left: 4px;
  width: 16px;
  height: 16px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--c-text-muted) 68%, white);
  box-shadow: 0 2px 5px rgb(15 23 42 / 0.18);
  transition:
    background-color 160ms ease,
    transform 180ms ease;
}

.checkboxInput:checked + .checkboxVisual {
  border-color: color-mix(in srgb, var(--c-primary) 52%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 24%, var(--c-surface));
  box-shadow:
    inset 0 1px 2px rgb(15 23 42 / 0.08),
    0 0 0 3px color-mix(in srgb, var(--c-primary) 10%, transparent);
}

.checkboxInput:checked + .checkboxVisual::after {
  background: var(--c-primary);
  transform: translateX(18px);
}

.checkboxInput:focus-visible + .checkboxVisual {
  outline: 2px solid color-mix(in srgb, var(--c-primary) 54%, transparent);
  outline-offset: 2px;
}

.checkboxInput:disabled + .checkboxVisual {
  opacity: 0.62;
}

.rangeField {
  min-height: 34px;
}

.rangeControl {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 44px;
  align-items: center;
  gap: 10px;
}

.rangeInput {
  width: 100%;
  min-width: 0;
  height: 18px;
  appearance: none;
  background: transparent;
  cursor: pointer;
}

.rangeInput::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 16%, var(--c-border));
  background: color-mix(in srgb, var(--c-surface) 48%, var(--c-bg));
}

.rangeInput::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  margin-top: -6px;
  border-radius: 999px;
  border: 2px solid color-mix(in srgb, var(--c-surface) 80%, white);
  background: var(--c-primary);
  box-shadow: 0 4px 10px rgb(15 23 42 / 0.18);
}

.rangeInput::-moz-range-track {
  height: 6px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 16%, var(--c-border));
  background: color-mix(in srgb, var(--c-surface) 48%, var(--c-bg));
}

.rangeInput::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 2px solid color-mix(in srgb, var(--c-surface) 80%, white);
  background: var(--c-primary);
  box-shadow: 0 4px 10px rgb(15 23 42 / 0.18);
}

.rangeInput:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--c-primary) 54%, transparent);
  outline-offset: 4px;
  border-radius: 999px;
}

.rangeValue {
  color: var(--c-text-muted);
  font-size: 12px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.readonlyValue {
  min-height: 34px;
  display: flex;
  align-items: center;
  min-width: 0;
  padding: 0 10px;
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  background: color-mix(in srgb, var(--c-surface) 70%, var(--c-bg));
  color: var(--c-text);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 420px) {
  .settingField {
    grid-template-columns: 1fr;
    align-items: stretch;
    gap: 6px;
  }
}
</style>
