<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { UserIcon } from "@heroicons/vue/24/outline";
import { useAuthStore } from "@/stores/auth.store";
import { bilibiliDesktop, type BilibiliLoginStatus, type BilibiliVideoInfo } from "@/infra/bilibili-desktop";
import BaseButton from "@/ui/base/BaseButton.vue";
import BaseInput from "@/ui/base/BaseInput.vue";
import BaseAvatar from "@/ui/base/BaseAvatar.vue";
import BaseCard from "@/ui/base/BaseCard.vue";
import AppIcon from "@/ui/base/AppIcon.vue";
import { useToastsStore } from "@/stores/toasts.store";
import { extractBilibiliVideoInput } from "@/features/room/video/bilibiliBvid";

const props = defineProps<{ active: boolean; canSelect: boolean }>();
const emit = defineEmits<{
  (e: "select-bilibili", value: { bvid: string; cid: number; page: number; mpd: string; duration: number }): void;
  (e: "clear-local"): void;
}>();
const { t } = useI18n();
const auth = useAuthStore();
const toasts = useToastsStore();
const status = ref<BilibiliLoginStatus | null>(null);
const pending = ref(false);
const failed = ref(false);
const loginWindowOpen = ref(false);
const videoInput = ref("");
const videoInfo = ref<BilibiliVideoInfo | null>(null);
const videoInfoPending = ref(false);
const selectedPage = ref(1);
const loadingPage = ref<number | null>(null);
const coverFailed = ref(false);
const statusChecked = ref(false);
let requestId = 0;
let videoInfoRequestId = 0;
let pageLoadRequestId = 0;

function formatDuration(seconds: number) {
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const rest = String(total % 60).padStart(2, "0");
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${rest}` : `${minutes}:${rest}`;
}

function clearVideoInfo() {
  videoInfoRequestId++;
  pageLoadRequestId++;
  videoInfo.value = null;
  videoInfoPending.value = false;
  loadingPage.value = null;
  coverFailed.value = false;
}

async function loadPage(page: number) {
  const part = videoInfo.value?.pages.find(item => item.page === page);
  if (!part || !bilibiliDesktop || !status.value?.loggedIn || !props.canSelect) return;
  const id = ++pageLoadRequestId;
  const bvid = videoInfo.value!.bvid;
  selectedPage.value = page;
  loadingPage.value = page;
  try {
    const { token, userId } = await currentAccount();
    const result = await bilibiliDesktop.resolve(token, bvid, part.cid);
    if (id !== pageLoadRequestId || auth.me?.id !== userId || !status.value?.loggedIn ||
      videoInfo.value?.bvid !== bvid) return;
    emit("select-bilibili", result);
  } catch {
    if (id === pageLoadRequestId) {
      toasts.push({ message: t("room.playback.errors.playFailed"), tone: "danger" });
    }
  } finally {
    if (id === pageLoadRequestId) loadingPage.value = null;
  }
}

function updateVideoInput(value: string) {
  videoInput.value = value;
  clearVideoInfo();
}

async function parseVideoInput() {
  if (!status.value?.loggedIn || !bilibiliDesktop || videoInfoPending.value) return;
  const parsed = extractBilibiliVideoInput(videoInput.value);
  if (!parsed) {
    toasts.push({ message: t("room.sourcePanel.bilibiliBvidNotFound"), tone: "warning" });
    return;
  }
  videoInput.value = parsed.bvid;
  clearVideoInfo();
  const id = videoInfoRequestId;
  videoInfoPending.value = true;
  try {
    const { token, userId } = await currentAccount();
    const result = await bilibiliDesktop.videoInfo(token, parsed.bvid);
    if (id !== videoInfoRequestId || auth.me?.id !== userId || !status.value?.loggedIn) return;
    videoInfo.value = result;
    selectedPage.value = result.pages.some(part => part.page === parsed.page)
      ? parsed.page : result.pages[0]?.page ?? 1;
  } catch {
    if (id === videoInfoRequestId) {
      toasts.push({ message: t("room.sourcePanel.bilibiliVideoInfoFailed"), tone: "danger" });
    }
  } finally {
    if (id === videoInfoRequestId) videoInfoPending.value = false;
  }
}

async function currentAccount() {
  const me = await auth.fetchMe();
  const token = localStorage.getItem("access_token");
  if (!token) throw new Error("ICINEMA_AUTH_REQUIRED");
  return { token, userId: me.id };
}

async function refreshStatus() {
  if (!bilibiliDesktop || !props.active) return;
  const id = ++requestId;
  statusChecked.value = true;
  pending.value = true;
  failed.value = false;
  try {
    const { token, userId } = await currentAccount();
    const result = await bilibiliDesktop.status(token);
    if (id !== requestId || auth.me?.id !== userId) return;
    status.value = result;
    if (result.loggedIn) loginWindowOpen.value = false;
    else {
      emit("clear-local");
      clearVideoInfo();
      videoInput.value = "";
    }
  } catch {
    if (id === requestId) failed.value = true;
  } finally {
    if (id === requestId) pending.value = false;
  }
}

async function openLogin() {
  if (!bilibiliDesktop || pending.value) return;
  pending.value = true;
  failed.value = false;
  try {
    const { token, userId } = await currentAccount();
    await bilibiliDesktop.login(token);
    if (auth.me?.id === userId && !status.value?.loggedIn) loginWindowOpen.value = true;
  } catch {
    failed.value = true;
  } finally {
    pending.value = false;
  }
}

async function logout() {
  if (!bilibiliDesktop || pending.value) return;
  pending.value = true;
  failed.value = false;
  try {
    const { token, userId } = await currentAccount();
    const result = await bilibiliDesktop.logout(token);
    if (auth.me?.id === userId) {
      status.value = result;
      emit("clear-local");
      loginWindowOpen.value = false;
      videoInput.value = "";
      clearVideoInfo();
    }
  } catch {
    failed.value = true;
  } finally {
    pending.value = false;
  }
}

const unsubscribe = bilibiliDesktop?.onLoginComplete(({ userId }) => {
  if (userId !== auth.me?.id) return;
  status.value = null;
  statusChecked.value = false;
  if (props.active) void refreshStatus();
});

watch(() => auth.me?.id, () => {
  emit("clear-local");
  requestId++;
  status.value = null;
  statusChecked.value = false;
  pending.value = false;
  failed.value = false;
  loginWindowOpen.value = false;
  videoInput.value = "";
  clearVideoInfo();
  if (props.active && auth.me?.id != null) void refreshStatus();
});

watch(() => props.active, active => {
  if (active && auth.me?.id != null && !statusChecked.value) void refreshStatus();
}, { immediate: true });

onBeforeUnmount(() => {
  requestId++;
  videoInfoRequestId++;
  pageLoadRequestId++;
  unsubscribe?.();
});
</script>

<template>
  <div class="bilibiliAccount">
    <div class="accountIdentity">
      <BaseAvatar :src="status?.loggedIn ? status.avatarUrl ?? undefined : undefined"
        :name="status?.loggedIn ? status.name : t('room.sourcePanel.bilibiliNotLoggedIn')"
        :alt="status?.loggedIn ? status.name : t('room.sourcePanel.bilibiliNotLoggedIn')"
        size="md" shape="circle" fit="cover" :border-width="1" loading="eager">
        <template #fallback><AppIcon :icon="UserIcon" :size="22" /></template>
      </BaseAvatar>
      <div class="accountStatus" role="status">
        {{ status?.loggedIn ? status.name || "Bilibili" : t("room.sourcePanel.bilibiliNotLoggedIn") }}
      </div>
      <div class="accountActions">
        <BaseButton v-if="failed || loginWindowOpen" :disabled="pending"
          :title="failed ? t('room.sourcePanel.bilibiliCheckFailed') : undefined" @click="refreshStatus">
          {{ t("room.sourcePanel.bilibiliRetry") }}
        </BaseButton>
        <BaseButton v-if="status?.loggedIn" variant="danger" :disabled="pending" @click="logout">
          {{ t("room.sourcePanel.bilibiliLogout") }}
        </BaseButton>
        <BaseButton v-else variant="primary" :disabled="pending" @click="openLogin">
          {{ t("room.sourcePanel.bilibiliLogin") }}
        </BaseButton>
      </div>
    </div>
    <form class="videoInputRow" @submit.prevent="parseVideoInput">
      <BaseInput :model-value="videoInput" :aria-label="t('room.sourcePanel.bilibiliVideoInput')"
        :placeholder="t('room.sourcePanel.bilibiliVideoInput')" :disabled="!status?.loggedIn"
        @update:model-value="updateVideoInput" />
      <BaseButton type="submit" variant="primary" :loading="videoInfoPending"
        :disabled="!status?.loggedIn || !videoInput.trim()">
        {{ t("room.sourcePanel.bilibiliParse") }}
      </BaseButton>
    </form>
    <BaseCard v-if="videoInfo" class="videoInfoCard">
      <div class="videoSummary">
        <img v-if="videoInfo.coverUrl && !coverFailed" class="videoCover" :src="videoInfo.coverUrl"
          :alt="videoInfo.title" referrerpolicy="no-referrer" @error="coverFailed = true" />
        <div class="videoDetails">
          <strong class="videoTitle">{{ videoInfo.title }}</strong>
          <span v-if="videoInfo.uploader">{{ t("room.sourcePanel.bilibiliUploader") }}：{{ videoInfo.uploader }}</span>
          <span>{{ t("room.sourcePanel.bilibiliDuration") }}：{{ formatDuration(videoInfo.durationSeconds) }}</span>
        </div>
      </div>
      <div v-if="videoInfo.pages.length" class="videoParts">
        <div class="partsHeading">{{ t("room.sourcePanel.bilibiliParts") }}</div>
        <div class="partsList" role="group" :aria-label="t('room.sourcePanel.bilibiliParts')">
          <BaseButton v-for="part in videoInfo.pages" :key="part.cid" class="partButton"
            :variant="selectedPage === part.page ? 'primary' : 'default'"
            :aria-pressed="selectedPage === part.page" :title="part.title"
            :loading="loadingPage === part.page" :disabled="loadingPage !== null || !canSelect"
            @click="loadPage(part.page)">
            <span class="partNumber">P{{ part.page }}</span>
            <span class="partTitle">{{ part.title }}</span>
            <span class="partDuration">{{ formatDuration(part.durationSeconds) }}</span>
          </BaseButton>
        </div>
      </div>
    </BaseCard>
  </div>
</template>

<style scoped>
.bilibiliAccount {
  display: grid;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--c-border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--c-surface) 82%, var(--c-bg));
}

.accountIdentity {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  min-width: 0;
}

.accountStatus {
  flex: 0 1 auto;
  min-width: 0;
  min-height: 18px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--c-text);
  font-size: 13px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.videoInputRow {
  position: relative;
}

.videoInputRow :deep(.inp) {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  height: 40px;
  padding-right: 88px;
  font-size: 12px;
}

.videoInputRow :deep(.inp:disabled) {
  opacity: 0.6;
  cursor: not-allowed;
}

.videoInputRow :deep(.btn) {
  position: absolute;
  top: 4px;
  right: 4px;
  height: 32px;
  min-height: 32px;
  padding: 0 12px;
  font-size: 12px;
}

.accountActions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  margin-left: auto;
  flex-shrink: 0;
}

.accountActions :deep(.btn) {
  min-height: 34px;
  height: 34px;
  font-size: 12px;
}

.videoInfoCard { display: grid; gap: 12px; min-width: 0; max-height: min(270px, 30vh); overflow-y: auto; overscroll-behavior: contain; }
.videoSummary { display: flex; align-items: stretch; gap: 12px; min-width: 0; }
.videoCover { width: 144px; aspect-ratio: 16 / 9; object-fit: cover; border-radius: var(--r-2); flex: 0 0 auto; }
.videoDetails { display: flex; flex-direction: column; justify-content: center; gap: 5px; min-width: 0; color: var(--c-text-muted); font-size: 12px; }
.videoTitle { color: var(--c-text); font-size: 14px; line-height: 1.4; overflow-wrap: anywhere; }
.videoParts { display: grid; gap: 8px; min-width: 0; }
.partsHeading { color: var(--c-text); font-size: 12px; font-weight: 600; }
.partsList { display: grid; gap: 6px; min-width: 0; }
.partButton { width: 100%; min-width: 0; }
.partButton :deep(.content) { display: flex; align-items: center; gap: 8px; width: 100%; min-width: 0; text-align: left; }
.partNumber, .partDuration { flex: 0 0 auto; font-size: 12px; }
.partTitle { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; }
@media (max-width: 560px) {
  .videoCover { width: 100px; }
}
</style>
