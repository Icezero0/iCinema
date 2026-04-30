<script setup lang="ts">
import { useI18n } from "vue-i18n";
import RoomRequestItem from "@/features/room/components/RoomRequestItem.vue";

defineProps<{
  loading?: boolean;
  error?: string | null;
  emptyLabel: string;
  items: Array<{
    id: number;
    user: string;
    note: string;
    time: string;
  }>;
  isRequestActionLoading: (requestId: number) => boolean;
}>();

const emit = defineEmits<{
  approve: [requestId: number];
  reject: [requestId: number];
}>();

const { t } = useI18n();
</script>

<template>
  <div
    class="panelBody requestsPanelBody"
    :class="{ stateOnly: loading || !!error || items.length === 0 }"
  >
    <div v-if="loading" class="panelState">
      {{ t("common.loading") }}
    </div>
    <div v-else-if="error" class="panelState error">
      {{ error }}
    </div>
    <div v-else-if="items.length === 0" class="panelState">
      {{ emptyLabel }}
    </div>
    <div v-else class="requestList">
      <RoomRequestItem
        v-for="request in items"
        :key="request.id"
        :user="request.user"
        :time="request.time"
        :note="request.note"
        :loading="isRequestActionLoading(request.id)"
        @approve="emit('approve', request.id)"
        @reject="emit('reject', request.id)"
      />
    </div>
  </div>
</template>

<style scoped>
.panelBody {
  display: grid;
  gap: 14px;
  padding: 14px;
  min-height: 0;
  align-content: start;
  overflow: auto;
}

.requestsPanelBody {
  height: 100%;
  min-height: 0;
  align-content: start;
}

.requestsPanelBody.stateOnly {
  display: flex;
  align-items: center;
  justify-content: center;
}

.requestsPanelBody.stateOnly > .panelState {
  height: auto;
  min-height: 0;
  align-self: auto;
}

.panelState {
  height: 100%;
  min-height: 0;
  display: grid;
  place-items: center;
  color: var(--c-text-muted);
  font-size: 13px;
  text-align: center;
}

.panelState.error {
  color: var(--c-danger);
}

.requestList {
  display: grid;
  gap: 10px;
}
</style>
