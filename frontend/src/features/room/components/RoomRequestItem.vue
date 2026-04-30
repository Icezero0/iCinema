<script setup lang="ts">
import { CheckIcon, XMarkIcon } from "@heroicons/vue/24/outline";

defineProps<{
  user: string;
  note: string;
  time: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  approve: [];
  reject: [];
}>();
</script>

<template>
  <div class="requestItem">
    <div class="requestText">
      <div class="requestUser">{{ user }}</div>
      <div class="requestNote">{{ note }}</div>
    </div>
    <div class="requestActions">
      <span class="requestTime">{{ time }}</span>
      <BaseIconButton
        class="miniAction approveAction"
        aria-label="Approve request"
        :disabled="loading"
        @click="emit('approve')"
      >
        <AppIcon :icon="CheckIcon" :size="18" />
      </BaseIconButton>
      <BaseIconButton
        class="miniAction rejectAction"
        aria-label="Reject request"
        :disabled="loading"
        @click="emit('reject')"
      >
        <AppIcon :icon="XMarkIcon" :size="18" />
      </BaseIconButton>
    </div>
  </div>
</template>

<style scoped>
.requestItem {
  padding: 12px;
  border: 1px solid var(--c-border);
  border-radius: 16px;
  background: color-mix(in srgb, var(--c-surface) 74%, var(--c-bg));
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.requestText {
  min-width: 0;
  flex: 1;
}

.requestUser {
  font-size: 14px;
  color: var(--c-text);
}

.requestNote,
.requestTime {
  margin-top: 4px;
  font-size: 12px;
  color: var(--c-text-muted);
}

.requestActions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.miniAction {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 82%, var(--c-bg));
}

.miniAction.approveAction {
  color: #2fb46e;
  border-color: color-mix(in srgb, #2fb46e 30%, var(--c-border));
}

.miniAction.approveAction:hover:not(:disabled) {
  background: color-mix(in srgb, #2fb46e 14%, var(--c-surface));
}

.miniAction.rejectAction {
  color: var(--c-danger);
  border-color: color-mix(in srgb, var(--c-danger) 30%, var(--c-border));
}

.miniAction.rejectAction:hover:not(:disabled) {
  background: color-mix(in srgb, var(--c-danger) 14%, var(--c-surface));
}

@media (max-width: 640px) {
  .requestItem {
    display: grid;
    grid-template-columns: 1fr;
    align-items: start;
    gap: 10px;
  }

  .requestText {
    width: 100%;
  }

  .requestActions {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    width: 100%;
    justify-content: stretch;
  }

  .requestTime {
    grid-column: 1 / -1;
    margin-top: 0;
  }

  .miniAction {
    width: 100%;
  }
}
</style>
