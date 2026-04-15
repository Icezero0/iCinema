<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { RoomJoinAuditMode } from "@/infra/api/rooms.api";

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    loading?: boolean;
    title: string;
    submitText: string;
    cancelText: string;
    nameLabel: string;
    namePlaceholder: string;
    visibilityLabel: string;
    visibilityPublicLabel: string;
    visibilityPrivateLabel: string;
    privateHint: string;
    joinAuditLabel: string;
    joinAuditHint: string;
    joinAuditManualLabel: string;
    joinAuditAutoApproveLabel: string;
    joinAuditAutoRejectLabel: string;
    defaultName?: string;
  }>(),
  {
    loading: false,
    defaultName: "",
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (
    e: "submit",
    payload: {
      name: string;
      visibility: "public" | "private";
      join_audit_mode: RoomJoinAuditMode;
    },
  ): void;
}>();

const name = ref("");
const visibility = ref<"public" | "private">("public");
const joinAuditMode = ref<RoomJoinAuditMode>("manual_review");

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    name.value = props.defaultName || "";
    visibility.value = "public";
    joinAuditMode.value = "manual_review";
  },
  { immediate: true },
);

const canSubmit = computed(() => name.value.trim().length > 0);

function close() {
  emit("update:modelValue", false);
}

function submit() {
  if (!canSubmit.value || props.loading) return;

  emit("submit", {
    name: name.value.trim(),
    visibility: visibility.value,
    join_audit_mode: joinAuditMode.value,
  });
}
</script>

<template>
  <BaseDialog
    :model-value="modelValue"
    aria-label="Create room dialog"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <BaseCard class="card">
      <div class="header">
        <h2 class="title">{{ title }}</h2>
      </div>

      <div class="form">
        <label class="field">
          <span class="label">{{ nameLabel }}</span>
          <BaseInput v-model="name" :placeholder="namePlaceholder" />
        </label>

        <label class="toggleRow">
          <span class="controlCopy">
            <span class="label">{{ visibilityLabel }}</span>
            <span class="hint">{{ privateHint }}</span>
          </span>

          <span class="segmentedControl" role="radiogroup" :aria-label="visibilityLabel">
            <button
              type="button"
              class="segment"
              :data-active="String(visibility === 'public')"
              @click="visibility = 'public'"
            >
              {{ visibilityPublicLabel }}
            </button>
            <button
              type="button"
              class="segment"
              :data-active="String(visibility === 'private')"
              @click="visibility = 'private'"
            >
              {{ visibilityPrivateLabel }}
            </button>
          </span>
        </label>

        <label class="toggleRow">
          <span class="controlCopy">
            <span class="label">{{ joinAuditLabel }}</span>
            <span class="hint">{{ joinAuditHint }}</span>
          </span>

          <span class="segmentedControl auditControl" role="radiogroup" :aria-label="joinAuditLabel">
            <button
              type="button"
              class="segment"
              :data-active="String(joinAuditMode === 'manual_review')"
              @click="joinAuditMode = 'manual_review'"
            >
              {{ joinAuditManualLabel }}
            </button>
            <button
              type="button"
              class="segment"
              :data-active="String(joinAuditMode === 'auto_approve')"
              @click="joinAuditMode = 'auto_approve'"
            >
              {{ joinAuditAutoApproveLabel }}
            </button>
            <button
              type="button"
              class="segment"
              :data-active="String(joinAuditMode === 'auto_reject')"
              @click="joinAuditMode = 'auto_reject'"
            >
              {{ joinAuditAutoRejectLabel }}
            </button>
          </span>
        </label>
      </div>

      <div class="actions">
        <BaseButton :disabled="loading" @click="close">
          {{ cancelText }}
        </BaseButton>

        <BaseButton
          variant="primary"
          :loading="loading"
          :disabled="!canSubmit"
          @click="submit"
        >
          {{ submitText }}
        </BaseButton>
      </div>
    </BaseCard>
  </BaseDialog>
</template>

<style scoped>
.card {
  padding: 20px;
  border-radius: 16px;
}

.header {
  margin-bottom: 14px;
}

.title {
  margin: 0;
  font-size: 18px;
  color: var(--c-text);
}

.form {
  display: grid;
  gap: 14px;
}

.field {
  display: grid;
  gap: 8px;
}

.label {
  font-size: 13px;
  color: var(--c-text);
}

.hint {
  font-size: 12px;
  color: var(--c-text-muted);
}

.toggleRow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  padding: 12px;
  background: color-mix(in srgb, var(--c-surface) 78%, var(--c-bg));
}

.controlCopy {
  display: grid;
  gap: 4px;
}

.segmentedControl {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px;
  border-radius: 999px;
  border: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 88%, var(--c-bg));
  flex: 0 0 auto;
}

.auditControl {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.segment {
  height: 32px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--c-text-muted);
  font-size: 13px;
  cursor: pointer;
  transition:
    background 160ms ease,
    color 160ms ease,
    box-shadow 160ms ease;
}

.segment[data-active="true"] {
  background: color-mix(in srgb, var(--c-primary) 16%, var(--c-surface));
  color: var(--c-text);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c-primary) 26%, var(--c-border));
}

.actions {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 640px) {
  .toggleRow {
    flex-direction: column;
    align-items: flex-start;
  }

  .segmentedControl,
  .auditControl {
    width: 100%;
  }

  .segment {
    flex: 1 1 auto;
  }

  .actions {
    justify-content: stretch;
  }
}
</style>
