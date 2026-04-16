<script setup lang="ts">
import type { Room } from "@/infra/api/rooms.api";
import RoomListItem from "@/features/rooms/home/RoomListItem.vue";

const props = defineProps<{
  title: string;
  hint: string;
  emptyText: string;
  requestText: string;
  requestedText: string;
  loadingText: string;
  rooms: Room[];
  loading?: boolean;
  submittingRoomIds?: number[];
  pendingRoomIds: number[];
}>();

defineEmits<{
  (e: "request", roomId: number): void;
}>();

function isPending(roomId: number) {
  return props.pendingRoomIds.includes(roomId);
}

function isSubmitting(roomId: number) {
  return props.submittingRoomIds?.includes(roomId) ?? false;
}
</script>

<template>
  <BaseCard class="sectionCard">
    <div v-if="loading" class="state">{{ loadingText }}</div>

    <div v-else-if="rooms.length === 0" class="empty">
      {{ emptyText }}
    </div>

    <div v-else class="list">
      <RoomListItem
        v-for="room in rooms"
        :key="room.id"
        :room="room"
        :action-label="isPending(room.id) ? requestedText : requestText"
        :action-loading="isSubmitting(room.id)"
        :action-disabled="isPending(room.id)"
        @action="$emit('request', room.id)"
      />
    </div>
  </BaseCard>
</template>

<style scoped>
.sectionCard {
  padding: 18px;
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
</style>
