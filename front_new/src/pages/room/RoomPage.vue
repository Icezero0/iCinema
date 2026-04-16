<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { getRoomById, type Room } from "@/infra/api/rooms.api";

const { t } = useI18n();
const route = useRoute();

const room = ref<Room | null>(null);
const isLoading = ref(false);
const error = ref("");

const roomId = computed(() => {
  const raw = route.params.id;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : 0;
});

async function fetchRoom() {
  if (!roomId.value) {
    error.value = t("room.invalidId");
    return;
  }

  isLoading.value = true;
  error.value = "";

  try {
    room.value = await getRoomById(roomId.value);
  } catch (e: any) {
    room.value = null;
    error.value =
      e?.response?.data?.detail ||
      e?.message ||
      t("room.loadFailed");
  } finally {
    isLoading.value = false;
  }
}

onMounted(fetchRoom);
watch(roomId, fetchRoom);
</script>

<template>
  <AppPageShell
    :title="room?.name || t('room.title')"
    :back-text="t('common.backHome')"
    :max-width="980"
  >
    <BaseCard class="card">
      <div v-if="isLoading" class="state">{{ t("common.loading") }}</div>

      <div v-else-if="error" class="state error">{{ error }}</div>

      <div v-else-if="room" class="content">
        <h2 class="name">{{ room.name }}</h2>
        <p class="summary">{{ t("room.placeholder") }}</p>

        <dl class="meta">
          <div class="row">
            <dt>{{ t("room.fields.id") }}</dt>
            <dd>#{{ room.id }}</dd>
          </div>
          <div class="row">
            <dt>{{ t("room.fields.owner") }}</dt>
            <dd>#{{ room.owner_id }}</dd>
          </div>
          <div class="row">
            <dt>{{ t("room.fields.visibility") }}</dt>
            <dd>
              {{
                room.visibility === "public"
                  ? t("room.fields.public")
                  : t("room.fields.private")
              }}
            </dd>
          </div>
        </dl>
      </div>
    </BaseCard>
  </AppPageShell>
</template>

<style scoped>
.card {
  padding: 22px;
}

.state {
  color: var(--c-text-muted);
  font-size: 14px;
}

.state.error {
  color: var(--c-danger);
}

.name {
  margin: 0;
  font-size: 24px;
  color: var(--c-text);
}

.summary {
  margin: 10px 0 0;
  color: var(--c-text-muted);
  line-height: 1.5;
}

.meta {
  margin: 20px 0 0;
  display: grid;
  gap: 10px;
}

.row {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 12px;
}

dt {
  color: var(--c-text-muted);
}

dd {
  margin: 0;
  color: var(--c-text);
}
</style>
