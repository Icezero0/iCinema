<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useI18n } from "vue-i18n";
import { MagnifyingGlassIcon } from "@heroicons/vue/24/outline";
import RoomListItem from "@/features/rooms/home/RoomListItem.vue";
import { listJoinRequests } from "@/infra/api/join-requests.api";
import { getRooms, type Room } from "@/infra/api/rooms.api";
import { useAuthStore } from "@/stores/auth.store";
import { useEntitiesStore } from "@/stores/entities.store";
import { useRoomsStore } from "@/stores/rooms.store";

const { t } = useI18n();
const auth = useAuthStore();
const entities = useEntitiesStore();
const rooms = useRoomsStore();

const filters = reactive({
  name: "",
  ownerUsername: "",
});

const appliedFilters = ref({
  name: "",
  ownerUsername: "",
});

const items = ref<Room[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 20;
const totalPages = computed(() =>
  Math.max(1, Math.ceil(total.value / pageSize)),
);
const isLoading = ref(false);
const error = ref("");
const existingPendingRoomIds = ref<number[]>([]);

const myRoomIds = computed(() => new Set(rooms.myRooms.map((room) => room.id)));

const pendingRoomIds = computed(() => {
  return new Set([...existingPendingRoomIds.value, ...rooms.pendingJoinRoomIds]);
});

const displayRooms = computed(() => {
  return items.value.map((room) => {
    const owner = entities.getUser(room.owner_id);

    return {
      ...room,
      owner_name: room.owner_name ?? owner?.username ?? owner?.email ?? null,
      owner_avatar_url: room.owner_avatar_url ?? owner?.avatar_url ?? null,
    } satisfies Room;
  });
});

async function fetchPendingJoinRequests() {
  try {
    const meId = auth.me?.id;
    if (!meId) {
      existingPendingRoomIds.value = [];
      return;
    }

    const data = await listJoinRequests({
      page: 1,
      page_size: 100,
      status: "pending",
      scope: "all_related_to_me",
    });

    existingPendingRoomIds.value = Array.from(
      new Set(
        data.items
          .filter(
            (item) =>
              item.initiator_user_id === meId || item.target_user_id === meId,
          )
          .map((item) => item.room_id),
      ),
    );
  } catch {
    existingPendingRoomIds.value = [];
  }
}

async function fetchPublicRooms() {
  isLoading.value = true;
  error.value = "";

  try {
    const data = await getRooms({
      page: page.value,
      page_size: pageSize,
      name: appliedFilters.value.name || null,
      owner_username: appliedFilters.value.ownerUsername || null,
    });

    items.value = data.items;
    total.value = data.total;
    entities.upsertRooms(data.items);
    await entities.ensureUsers(data.items.map((room) => room.owner_id));
  } catch (e: any) {
    error.value =
      e?.response?.data?.detail || e?.message || t("publicRooms.loadFailed");
  } finally {
    isLoading.value = false;
  }
}

async function bootstrap() {
  if (!rooms.isLoading && rooms.myRooms.length === 0) {
    await rooms.fetchHomeRooms();
  }

  await Promise.all([fetchPublicRooms(), fetchPendingJoinRequests()]);
}

async function handleSearch() {
  appliedFilters.value = {
    name: filters.name.trim(),
    ownerUsername: filters.ownerUsername.trim(),
  };
  page.value = 1;
  await fetchPublicRooms();
}

async function handleRequestJoin(roomId: number) {
  await rooms.requestToJoin(roomId);
}

async function goPrevPage() {
  if (page.value <= 1) return;
  page.value -= 1;
  await fetchPublicRooms();
}

async function goNextPage() {
  if (page.value >= totalPages.value) return;
  page.value += 1;
  await fetchPublicRooms();
}

function actionLabel(roomId: number) {
  const room = items.value.find((value) => value.id === roomId);

  if (myRoomIds.value.has(roomId)) return t("publicRooms.inRoom");
  if (pendingRoomIds.value.has(roomId)) return t("publicRooms.requested");
  if (room?.join_audit_mode === "auto_reject") {
    return t("publicRooms.notAllowed");
  }
  return t("publicRooms.request");
}

function actionDisabled(roomId: number) {
  const room = items.value.find((value) => value.id === roomId);

  return (
    myRoomIds.value.has(roomId) ||
    pendingRoomIds.value.has(roomId) ||
    room?.join_audit_mode === "auto_reject"
  );
}

onMounted(() => {
  void bootstrap();
});
</script>

<template>
  <AppPageShell
    :title="t('publicRooms.title')"
    :back-text="t('common.backHome')"
    :max-width="980"
  >
    <template #toolbar>
      <BaseCard class="toolbarCard">
        <form class="searchBar" @submit.prevent="handleSearch">
          <label class="searchField">
            <span class="searchLabel">{{ t("publicRooms.filters.nameLabel") }}</span>
            <BaseInput v-model="filters.name" />
          </label>

          <label class="searchField">
            <span class="searchLabel">{{
              t("publicRooms.filters.ownerUsernameLabel")
            }}</span>
            <BaseInput v-model="filters.ownerUsername" />
          </label>

          <BaseIconButton
            class="searchButton"
            type="submit"
            :aria-label="t('publicRooms.filters.search')"
          >
            <AppIcon :icon="MagnifyingGlassIcon" :size="18" />
          </BaseIconButton>
        </form>
      </BaseCard>
    </template>

    <BaseCard class="card">
      <div v-if="isLoading" class="state">{{ t("common.loading") }}</div>
      <div v-else-if="error" class="state error">{{ error }}</div>
      <div v-else-if="displayRooms.length === 0" class="state">
        {{ t("publicRooms.empty") }}
      </div>

      <div v-else class="list">
        <RoomListItem
          v-for="room in displayRooms"
          :key="room.id"
          :room="room"
          :action-label="actionLabel(room.id)"
          :action-disabled="actionDisabled(room.id)"
          :action-loading="rooms.submittingJoinRoomIds.includes(room.id)"
          @action="handleRequestJoin(room.id)"
        />
      </div>

      <div class="pagination">
        <BaseButton :disabled="page <= 1 || isLoading" @click="goPrevPage">
          {{ t("publicRooms.pagination.prev") }}
        </BaseButton>
        <span class="pageInfo">
          {{
            t("publicRooms.pagination.pageInfo", {
              page,
              totalPages,
              total,
            })
          }}
        </span>
        <BaseButton
          :disabled="page >= totalPages || isLoading"
          @click="goNextPage"
        >
          {{ t("publicRooms.pagination.next") }}
        </BaseButton>
      </div>
    </BaseCard>
  </AppPageShell>
</template>

<style scoped>
.toolbarCard {
  padding: 14px 18px;
}

.card {
  padding: 18px;
}

.searchBar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
}

.searchField {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.searchLabel {
  font-size: 12px;
  color: var(--c-text-muted);
  white-space: nowrap;
}

.searchField :deep(.inp) {
  width: 180px;
  max-width: 26vw;
}

.searchButton {
  margin-left: auto;
  margin-bottom: 1px;
}

.list {
  display: grid;
  gap: 10px;
}

.state {
  padding: 20px 6px;
  color: var(--c-text-muted);
  font-size: 13px;
}

.state.error {
  color: var(--c-danger);
}

.pagination {
  margin-top: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.pageInfo {
  font-size: 12px;
  color: var(--c-text-muted);
}

@media (max-width: 800px) {
  .searchBar {
    display: grid;
    grid-template-columns: 1fr;
  }

  .searchButton,
  .pagination {
    justify-content: stretch;
  }

  .searchField {
    display: grid;
    gap: 6px;
  }

  .searchField :deep(.inp) {
    width: 100%;
    max-width: 100%;
  }

  .pagination :deep(button) {
    flex: 1 1 0;
  }

  .searchButton {
    margin-left: 0;
    justify-self: end;
  }
}
</style>
