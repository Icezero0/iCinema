<script setup lang="ts">
import { computed, ref, watch } from "vue";

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
    publicLabel: string;
    privateHint: string;
    defaultName?: string;
  }>(),
  {
    loading: false,
    defaultName: "",
  },
);

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "submit", payload: { name: string; visibility: "public" | "private" }): void;
}>();

const name = ref("");
const isPublic = ref(true);

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return;
    name.value = props.defaultName || "";
    isPublic.value = true;
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
    visibility: isPublic.value ? "public" : "private",
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
          <span class="toggleCopy">
            <span class="label">{{ visibilityLabel }}</span>
            <span class="hint">{{ privateHint }}</span>
          </span>

          <span class="toggleControl">
            <input v-model="isPublic" class="checkbox" type="checkbox" />
            <span class="toggleText">{{ publicLabel }}</span>
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

.toggleCopy {
  display: grid;
  gap: 4px;
}

.toggleControl {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--c-text);
  flex: 0 0 auto;
}

.checkbox {
  width: 16px;
  height: 16px;
  margin: 0;
}

.toggleText {
  font-size: 13px;
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

  .actions {
    justify-content: stretch;
  }
}
</style>
