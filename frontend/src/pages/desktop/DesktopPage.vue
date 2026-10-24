<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { ArrowDownTrayIcon, ArrowPathIcon, ComputerDesktopIcon, DevicePhoneMobileIcon, FolderOpenIcon } from "@heroicons/vue/24/outline";
import { windowsInstallerDownloadUrl, windowsPortableDownloadUrl } from "@/config/desktop";
import { desktop, type DesktopInfo, type DesktopUpdate } from "@/infra/desktop";
import { useToastsStore } from "@/stores/toasts.store";

const { t, locale } = useI18n();
const toasts = useToastsStore();
const info = ref<DesktopInfo | null>(null);
const update = ref<DesktopUpdate | null>(null);
const checking = ref(false);
const openingFolder = ref(false);
const upcomingPlatforms = [
  { name: "Android", icon: DevicePhoneMobileIcon },
  { name: "iOS", icon: DevicePhoneMobileIcon },
  { name: "macOS", icon: ComputerDesktopIcon },
];
const checkedAt = computed(() => update.value
  ? new Date(update.value.checkedAt).toLocaleString(locale.value) : "");

async function checkForUpdates() {
  if (!desktop || checking.value) return;
  checking.value = true;
  try {
    info.value ??= await desktop.getInfo();
    update.value = await desktop.checkForUpdates();
  } catch {
    toasts.push({ message: t("desktopApp.checkFailed"), tone: "danger" });
  } finally {
    checking.value = false;
  }
}

async function openDataFolder() {
  if (!desktop || openingFolder.value) return;
  openingFolder.value = true;
  try {
    await desktop.openDataFolder();
  } catch {
    toasts.push({ message: t("desktopApp.openFolderFailed"), tone: "danger" });
  } finally {
    openingFolder.value = false;
  }
}

onMounted(() => { if (desktop) void checkForUpdates(); });
</script>

<template>
  <AppPageShell :title="t(desktop ? 'desktopApp.about' : 'desktopApp.title')" :max-width="960">
    <div class="desktopPage">
      <BaseCard class="overview">
        <div class="identity">
          <img class="logo" src="/favicon.ico" alt="" width="72" height="72" />
          <div class="identityText">
            <h2>iCinema</h2>
            <p v-if="desktop" class="version">{{ t('desktopApp.version') }} {{ info ? `v${info.version}` : '—' }}</p>
          </div>
        </div>

        <template v-if="desktop">
          <div class="updateRow">
            <div class="updateState" role="status" aria-live="polite">
              <span v-if="checking">{{ t('desktopApp.checking') }}</span>
              <span v-else-if="update?.status === 'available'" class="newVersion">
                {{ t('desktopApp.available', { version: update.latestVersion }) }}
              </span>
              <span v-else-if="update?.status === 'current'">{{ t('desktopApp.current') }}</span>
              <span v-else-if="update?.status === 'unpublished'">{{ t('desktopApp.unpublished') }}</span>
              <span v-else>{{ t('desktopApp.notChecked') }}</span>
              <span v-if="checkedAt && !checking" class="checkedAt">{{ t('desktopApp.checkedAt', { time: checkedAt }) }}</span>
            </div>
            <div class="actions">
              <BaseButton :loading="checking" @click="checkForUpdates">
                <span class="buttonContent"><AppIcon :icon="ArrowPathIcon" :size="16" />{{ t('desktopApp.check') }}</span>
              </BaseButton>
              <a v-if="update?.status === 'available'" class="downloadButton" :href="update.releaseUrl" target="_blank" rel="noopener noreferrer">
                <AppIcon :icon="ArrowDownTrayIcon" :size="16" />{{ t('desktopApp.getUpdate') }}
              </a>
            </div>
          </div>
        </template>
      </BaseCard>

      <BaseCard v-if="desktop && info" class="dataCard">
        <div class="dataHeading">
          <h2>{{ t('desktopApp.dataLocation') }}</h2>
          <BaseButton :loading="openingFolder" @click="openDataFolder">
            <span class="buttonContent"><AppIcon :icon="FolderOpenIcon" :size="16" />{{ t('desktopApp.openFolder') }}</span>
          </BaseButton>
        </div>
        <p class="storagePath">{{ info.storagePath }}</p>
      </BaseCard>

      <div v-if="!desktop" class="platforms">
        <BaseCard class="platformCard windowsCard">
          <div class="platformHeading">
            <span class="platformIcon"><AppIcon :icon="ComputerDesktopIcon" :size="26" /></span>
            <div>
              <h2>Windows</h2>
              <span class="platformDetail">64-bit</span>
            </div>
          </div>
          <div class="platformDownloads">
            <div class="edition">
              <a v-if="windowsInstallerDownloadUrl" class="downloadButton secondary" :href="windowsInstallerDownloadUrl" target="_blank" rel="noopener noreferrer">
                <AppIcon :icon="ArrowDownTrayIcon" :size="16" />{{ t('desktopApp.installer') }}
              </a>
              <BaseButton v-else disabled :aria-label="`${t('desktopApp.installer')} · ${t('desktopApp.notReleased')}`">{{ t('desktopApp.installer') }}</BaseButton>
              <span v-if="!windowsInstallerDownloadUrl" class="availability">{{ t('desktopApp.notReleased') }}</span>
            </div>
            <div class="edition">
              <a v-if="windowsPortableDownloadUrl" class="downloadButton" :href="windowsPortableDownloadUrl" target="_blank" rel="noopener noreferrer">
                <AppIcon :icon="ArrowDownTrayIcon" :size="16" />{{ t('desktopApp.portable') }}
              </a>
              <BaseButton v-else disabled>{{ t('desktopApp.portable') }}</BaseButton>
              <span v-if="!windowsPortableDownloadUrl" class="availability">{{ t('desktopApp.downloadUnavailable') }}</span>
            </div>
          </div>
        </BaseCard>
        <BaseCard v-for="platform in upcomingPlatforms" :key="platform.name" class="platformCard upcomingCard">
          <div class="platformHeading">
            <span class="platformIcon"><AppIcon :icon="platform.icon" :size="26" /></span>
            <h2>{{ platform.name }}</h2>
          </div>
          <span class="developmentStatus">{{ t('desktopApp.inDevelopment') }}</span>
        </BaseCard>
      </div>
    </div>
  </AppPageShell>
</template>

<style scoped>
.desktopPage { display: grid; gap: 18px; }
.overview, .dataCard { padding: 28px; }
.overview { background: linear-gradient(135deg, color-mix(in srgb, var(--c-primary) 7%, var(--c-surface)), var(--c-surface) 70%); }
.identity { display: flex; align-items: center; gap: 20px; }
.logo { flex: 0 0 auto; border-radius: 16px; }
.identityText { min-width: 0; }
h2 { margin: 0; font-size: 18px; color: var(--c-text); }
.identity h2 { font-size: 28px; }
p { margin: 8px 0 0; color: var(--c-text-muted); font-size: 14px; line-height: 1.65; }
.version { font-variant-numeric: tabular-nums; }
.updateRow { display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-top: 28px; padding-top: 24px; border-top: 1px solid var(--c-border); }
.actions, .buttonContent { display: inline-flex; align-items: center; gap: 8px; }
.actions { flex-wrap: wrap; flex-shrink: 0; }
.downloadButton { min-height: 40px; display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 0 16px; border-radius: var(--r-2); background: var(--c-primary); color: var(--c-primary-text); text-decoration: none; font-weight: 500; white-space: nowrap; transition: background 150ms ease; }
.downloadButton:hover { background: var(--c-primary-hover); }
.downloadButton.secondary { border: 1px solid var(--c-border); background: var(--c-surface); color: var(--c-text); }
.downloadButton.secondary:hover { background: var(--c-hover); }
.downloadButton:focus-visible { outline: 2px solid var(--c-primary); outline-offset: 3px; }
.updateState { display: grid; gap: 8px; font-size: 14px; }
.newVersion { color: var(--c-primary); font-weight: 600; }
.checkedAt { color: var(--c-text-muted); font-size: 12px; }
.dataHeading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.storagePath { overflow-wrap: anywhere; user-select: text; }
.platforms { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.platformCard { padding: 24px; }
.windowsCard { grid-column: 1 / -1; display: flex; align-items: center; justify-content: space-between; gap: 24px; }
.platformHeading { display: flex; align-items: center; gap: 14px; }
.platformIcon { display: inline-flex; flex-shrink: 0; padding: 12px; border-radius: var(--r-2); background: color-mix(in srgb, var(--c-primary) 10%, transparent); color: var(--c-primary); }
.platformDetail { display: block; margin-top: 6px; color: var(--c-text-muted); font-size: 12px; }
.platformDownloads { display: flex; align-self: stretch; align-items: flex-start; gap: 12px; }
.edition { display: grid; gap: 8px; min-width: 112px; text-align: center; }
.availability { color: var(--c-text-muted); font-size: 12px; }
.upcomingCard { display: grid; gap: 24px; }
.developmentStatus { color: var(--c-text-muted); font-size: 13px; }
@media (max-width: 720px) {
  .platforms { grid-template-columns: 1fr; }
  .overview, .dataCard { padding: 20px; }
  .updateRow, .windowsCard { align-items: flex-start; flex-direction: column; }
  .identity { gap: 14px; }
  .logo { width: 56px; height: 56px; }
  .dataHeading { flex-wrap: wrap; }
}
</style>
