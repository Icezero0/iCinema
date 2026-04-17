<script setup lang="ts">
defineProps<{
  user: string;
  note: string;
  time: string;
  approveLabel: string;
  rejectLabel: string;
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
      <button class="miniAction primary" type="button">{{ approveLabel }}</button>
      <button class="miniAction" type="button">{{ rejectLabel }}</button>
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
  height: 32px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text);
  cursor: pointer;
}

.miniAction.primary {
  border-color: transparent;
  background: var(--c-primary);
  color: var(--c-primary-text);
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
    justify-content: center;
  }
}
</style>
