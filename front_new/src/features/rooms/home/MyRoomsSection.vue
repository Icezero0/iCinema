<script setup lang="ts">
import type { Room } from "@/infra/api/rooms.api";
import RoomListItem from "@/features/rooms/home/RoomListItem.vue";

defineProps<{
  title: string;
  hint: string;
  emptyText: string;
  createText: string;
  joinText: string;
  enterText: string;
  loadingText: string;
  rooms: Room[];
  loading?: boolean;
}>();

defineEmits<{
  (e: "create"): void;
  (e: "join"): void;
  (e: "enter", roomId: number): void;
}>();
</script>

<template>
  <BaseCard class="sectionCard">
    <div class="header">
      <div class="titleBlock">
        <h2 class="title">{{ title }}</h2>
        <p class="hint">{{ hint }}</p>
      </div>

      <div class="actions">
        <BaseButton @click="$emit('join')">
          {{ joinText }}
        </BaseButton>

        <BaseButton variant="primary" @click="$emit('create')">
          {{ createText }}
        </BaseButton>
      </div>
    </div>

    <div v-if="loading" class="state">{{ loadingText }}</div>

    <div v-else-if="rooms.length === 0" class="empty">
      {{ emptyText }}
    </div>

    <div v-else class="list">
      <RoomListItem
        v-for="room in rooms"
        :key="room.id"
        :room="room"
        :action-label="enterText"
        action-variant="primary"
        @action="$emit('enter', room.id)"
      />
    </div>
  </BaseCard>
</template>

<style scoped>
.sectionCard {
  padding: 18px;
}

.header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 16px;
}

.title {
  margin: 0;
  font-size: 18px;
  color: var(--c-text);
}

.hint {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--c-text-muted);
}

.actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.list {
  display: grid;
  gap: 10px;
}

.state,
.empty {
  padding: 20px 6px;
  color: var(--c-text-muted);
  font-size: 13px;
}

@media (max-width: 640px) {
  .header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
