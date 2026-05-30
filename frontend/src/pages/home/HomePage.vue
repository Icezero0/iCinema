<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuthStore } from "@/stores/auth.store";
import { useRoomsStore } from "@/stores/rooms.store";
import HomeHero from "@/features/home/HomeHero.vue";
import MyRoomsSection from "@/features/rooms/home/MyRoomsSection.vue";
import CreateRoomDialog from "@/features/rooms/home/CreateRoomDialog.vue";

const { t } = useI18n();
const router = useRouter();
const auth = useAuthStore();
const rooms = useRoomsStore();

const dialogOpen = ref(false);
const feedback = ref("");
const feedbackTone = ref<"default" | "danger">("default");

const userName = computed(() => auth.me?.username || auth.me?.email || "User");
const defaultRoomName = computed(
  () => `${userName.value}${t("home.create.defaultSuffix")}`,
);

onMounted(() => {
  void (async () => {
    await rooms.fetchHomeRooms();
  })();
});

async function handleCreateRoom(payload: {
  name: string;
  visibility: "public" | "private";
  join_audit_mode: "auto_approve" | "manual_review" | "auto_reject";
}) {
  feedback.value = "";

  try {
    const created = await rooms.createOwnedRoom(payload);
    dialogOpen.value = false;
    feedbackTone.value = "default";
    feedback.value = t("home.feedback.roomCreated", { room: created.name });
  } catch (error: any) {
    feedbackTone.value = "danger";
    feedback.value = error?.message || t("home.feedback.createFailed");
  }
}

function openCreateDialog() {
  dialogOpen.value = true;
}

function openPublicRooms() {
  router.push("/public-rooms");
}

function enterRoom(roomId: number) {
  router.push(`/rooms/${roomId}`);
}

</script>

<template>
  <div class="page">
    <CreateRoomDialog
      v-model="dialogOpen"
      :loading="rooms.isCreating"
      :title="t('home.create.title')"
      :submit-text="t('home.create.submit')"
      :cancel-text="t('common.cancel')"
      :name-label="t('home.create.nameLabel')"
      :name-placeholder="t('home.create.namePlaceholder')"
      :visibility-label="t('home.create.visibilityLabel')"
      :visibility-public-label="t('home.create.visibilityPublicLabel')"
      :visibility-private-label="t('home.create.visibilityPrivateLabel')"
      :private-hint="t('home.create.privateHint')"
      :join-audit-label="t('home.create.joinAuditLabel')"
      :join-audit-hint="t('home.create.joinAuditHint')"
      :join-audit-manual-label="t('home.create.joinAuditManualLabel')"
      :join-audit-auto-approve-label="t('home.create.joinAuditAutoApproveLabel')"
      :join-audit-auto-reject-label="t('home.create.joinAuditAutoRejectLabel')"
      :default-name="defaultRoomName"
      @submit="handleCreateRoom"
    />

    <BaseLayout :max-width="1120">
      <HomeHero
        :title="t('home.headline', { name: userName })"
      />

      <p
        v-if="feedback || rooms.error"
        class="feedback"
        :data-tone="rooms.error || feedbackTone === 'danger' ? 'danger' : 'default'"
      >
        {{ feedback || rooms.error }}
      </p>

      <div class="topGrid">
        <MyRoomsSection
          :title="t('home.myRooms.title')"
          :hint="t('home.myRooms.hint')"
          :empty-text="t('home.myRooms.empty')"
          :create-text="t('home.myRooms.create')"
          :join-text="t('home.myRooms.join')"
          :enter-text="t('home.myRooms.enter')"
          :loading-text="t('common.loading')"
          :rooms="rooms.myRooms"
          :loading="rooms.isLoading"
          @create="openCreateDialog"
          @join="openPublicRooms"
          @enter="enterRoom"
        />
      </div>
    </BaseLayout>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
}

.feedback {
  margin: 16px 0 0;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 72%, var(--c-bg));
  color: var(--c-text);
  font-size: 13px;
}

.feedback[data-tone="danger"] {
  color: var(--c-danger);
  border-color: color-mix(in srgb, var(--c-danger) 28%, var(--c-border));
}

.topGrid {
  margin-top: 20px;
}
</style>
