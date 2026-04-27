<script setup lang="ts">
import type { Room } from "@/infra/api/rooms.api";

defineProps<{
  room: Room;
  roomNameLabel: string;
  visibilityLabel: string;
  syncPolicyLabel: string;
  syncPolicyValue: string;
  syncPermissionLabel: string;
  syncPermissionValue: string;
  localSyncTitle: string;
  localSyncHint: string;
  infoTitle: string;
  syncTitle: string;
  advancedTitle: string;
  advancedHint: string;
  publicLabel: string;
  privateLabel: string;
  localSyncStrategy: string;
  localSyncOptions: { value: string; label: string }[];
}>();

const emit = defineEmits<{
  (e: "update:localSyncStrategy", value: string): void;
}>();
</script>

<template>
  <div class="settingsStack">
    <div class="settingsSection">
      <div class="sectionTitle">{{ infoTitle }}</div>
      <div class="settingRow">
        <span>{{ roomNameLabel }}</span>
        <span class="settingValue">{{ room.name }}</span>
      </div>
      <div class="settingRow">
        <span>{{ visibilityLabel }}</span>
        <span class="settingValue">{{ room.visibility === "public" ? publicLabel : privateLabel }}</span>
      </div>
    </div>

    <div class="settingsSection">
      <div class="sectionTitle">{{ syncTitle }}</div>
      <div class="settingRow">
        <span>{{ syncPolicyLabel }}</span>
        <span class="settingValue">{{ syncPolicyValue }}</span>
      </div>
      <div class="settingRow">
        <span>{{ syncPermissionLabel }}</span>
        <span class="settingValue">{{ syncPermissionValue }}</span>
      </div>
      <div class="settingSelect">
        <span class="settingSelectLabel">{{ localSyncTitle }}</span>
        <span class="settingSelectHint">{{ localSyncHint }}</span>
        <BaseSelect
          :model-value="localSyncStrategy"
          class="settingsSelect"
          :options="localSyncOptions"
          :width="220"
          max-width="100%"
          @update:model-value="emit('update:localSyncStrategy', $event)"
        />
      </div>
    </div>

    <div class="settingsSection folded">
      <div class="sectionTitle">{{ advancedTitle }}</div>
      <div class="settingFoldHint">{{ advancedHint }}</div>
    </div>
  </div>
</template>

<style scoped>
.settingsStack {
  display: grid;
  gap: 10px;
}

.settingsSection {
  padding: 12px;
  border: 1px solid var(--c-border);
  border-radius: 16px;
  background: color-mix(in srgb, var(--c-surface) 74%, var(--c-bg));
  display: grid;
  gap: 10px;
}

.settingsSection.folded {
  background: color-mix(in srgb, var(--c-surface) 68%, var(--c-bg));
}

.sectionTitle {
  font-size: 13px;
  font-weight: 650;
  color: var(--c-text);
}

.settingRow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
  color: var(--c-text-muted);
}

.settingValue {
  color: var(--c-text);
}

.settingSelect {
  display: grid;
  gap: 6px;
}

.settingSelectLabel {
  font-size: 13px;
  color: var(--c-text-muted);
}

.settingSelectHint {
  font-size: 12px;
  color: var(--c-text-muted);
}

.settingFoldHint {
  font-size: 12px;
  color: var(--c-text-muted);
}
</style>
