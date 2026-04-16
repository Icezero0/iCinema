<script setup lang="ts">
import { onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { useRoomsStore } from "@/stores/rooms.store";
import PublicRoomsSection from "@/features/rooms/home/PublicRoomsSection.vue";

const { t } = useI18n();
const rooms = useRoomsStore();

onMounted(() => {
  void rooms.fetchHomeRooms();
});

async function handleRequestJoin(roomId: number) {
  await rooms.requestToJoin(roomId);
}

</script>

<template>
  <AppPageShell
    :title="t('publicRooms.title')"
    :back-text="t('common.backHome')"
    :max-width="980"
  >
    <PublicRoomsSection
      :title="t('publicRooms.title')"
      :hint="t('publicRooms.hint')"
      :empty-text="t('publicRooms.empty')"
      :request-text="t('publicRooms.request')"
      :requested-text="t('publicRooms.requested')"
      :loading-text="t('common.loading')"
      :rooms="rooms.publicRooms"
      :loading="rooms.isLoading"
      :pending-room-ids="rooms.pendingJoinRoomIds"
      @request="handleRequestJoin"
    />
  </AppPageShell>
</template>
