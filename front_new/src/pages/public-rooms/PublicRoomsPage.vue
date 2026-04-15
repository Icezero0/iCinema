<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useRoomsStore } from "@/stores/rooms.store";
import PublicRoomsSection from "@/features/rooms/home/PublicRoomsSection.vue";

const { t } = useI18n();
const router = useRouter();
const rooms = useRoomsStore();

onMounted(() => {
  void rooms.fetchHomeRooms();
});

async function handleRequestJoin(roomId: number) {
  await rooms.requestToJoin(roomId);
}

function goHome() {
  router.push("/");
}
</script>

<template>
  <BaseLayout :title="t('publicRooms.title')" :max-width="980">
    <div class="topBar">
      <BaseButton @click="goHome">
        {{ t("common.backHome") }}
      </BaseButton>
    </div>

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
  </BaseLayout>
</template>

<style scoped>
.topBar {
  margin-bottom: 16px;
}
</style>
