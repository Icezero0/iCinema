<script setup lang="ts">
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";

const router = useRouter();
const { t } = useI18n();

function goNotifications() {
  router.push("/notifications");
}
</script>

<template>
  <BaseLayout :title="t('joinRequests.title')" :max-width="920">
    <BaseCard class="card">
      <h2 class="headline">{{ t("joinRequests.placeholderTitle") }}</h2>
      <p class="copy">{{ t("joinRequests.placeholderBody") }}</p>

      <div class="actions">
        <BaseButton @click="goNotifications">
          {{ t("joinRequests.openNotifications") }}
        </BaseButton>
      </div>
    </BaseCard>
  </BaseLayout>
</template>

<style scoped>
.card {
  padding: 22px;
}

.headline {
  margin: 0;
  font-size: 22px;
  color: var(--c-text);
}

.copy {
  margin: 10px 0 0;
  color: var(--c-text-muted);
  line-height: 1.6;
}

.actions {
  margin-top: 18px;
}
</style>
