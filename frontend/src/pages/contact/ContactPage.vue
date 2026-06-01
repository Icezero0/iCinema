<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import {
  EnvelopeIcon,
} from "@heroicons/vue/24/outline";
import { contactConfig } from "@/config/contact";
import ContactMethodGrid from "@/features/feedback/components/ContactMethodGrid.vue";
import ScreenshotUploadGrid from "@/features/feedback/components/ScreenshotUploadGrid.vue";
import { MAX_FEEDBACK_SCREENSHOT_COUNT } from "@/features/feedback/constants";
import { useLocalImagePreviews } from "@/features/feedback/composables/useLocalImagePreviews";
import type { ContactMethodItem } from "@/features/feedback/types";
import {
  createFeedback,
  type FeedbackPage,
  type FeedbackType,
} from "@/infra/api/feedback.api";
import { getBackendErrorMessage } from "@/infra/http/client";
import { useAuthStore } from "@/stores/auth.store";
import { useToastsStore } from "@/stores/toasts.store";
import GitHubIcon from "@/ui/icons/GitHubIcon.vue";
import QfacePenguinIcon from "@/ui/icons/QfacePenguinIcon.vue";

const { t } = useI18n();
const auth = useAuthStore();
const toasts = useToastsStore();

const contactEmail = contactConfig.email.trim();
const contactGithub = contactConfig.github.trim();
const contactQQ = contactConfig.qq.trim();
const feedbackType = ref<FeedbackType>("bug");
const feedbackPage = ref<FeedbackPage>("room");
const feedbackTitle = ref("");
const feedbackDescription = ref("");
const isSubmittingFeedback = ref(false);
const feedbackError = ref("");
const {
  previews: feedbackScreenshots,
  addFiles: addScreenshotFiles,
  removePreview: removeScreenshot,
  clearPreviews: clearScreenshots,
} = useLocalImagePreviews({ maxCount: MAX_FEEDBACK_SCREENSHOT_COUNT });

const methods = computed<ContactMethodItem[]>(() => {
  const items: ContactMethodItem[] = [];

  if (contactGithub) {
    items.push({
      key: "github",
      title: t("contact.methods.github.title"),
      value: contactGithub,
      href: contactGithub,
      action: t("contact.methods.github.action"),
      icon: GitHubIcon,
    });
  }

  if (contactEmail) {
    items.push({
      key: "email",
      title: t("contact.methods.email.title"),
      value: contactEmail,
      href: `mailto:${contactEmail}`,
      action: t("contact.methods.email.action"),
      icon: EnvelopeIcon,
    });
  }

  if (contactQQ) {
    items.push({
      key: "qq",
      title: t("contact.methods.qq.title"),
      value: contactQQ,
      href: `tencent://message/?uin=${encodeURIComponent(contactQQ)}`,
      action: t("contact.methods.qq.action"),
      icon: QfacePenguinIcon,
    });
  }

  return items;
});

const feedbackTypeOptions = computed(() => [
  { value: "bug", label: t("contact.feedback.types.bug") },
  { value: "suggestion", label: t("contact.feedback.types.suggestion") },
  { value: "experience", label: t("contact.feedback.types.experience") },
  { value: "other", label: t("contact.feedback.types.other") },
]);

const feedbackPageOptions = computed(() => [
  { value: "room", label: t("contact.feedback.pages.room") },
  { value: "home", label: t("contact.feedback.pages.home") },
  { value: "public_rooms", label: t("contact.feedback.pages.publicRooms") },
  { value: "join_requests", label: t("contact.feedback.pages.joinRequests") },
  { value: "notifications", label: t("contact.feedback.pages.notifications") },
  { value: "profile", label: t("contact.feedback.pages.profile") },
  { value: "contact", label: t("contact.feedback.pages.contact") },
  { value: "other", label: t("contact.feedback.pages.other") },
]);

const canSubmitFeedback = computed(
  () =>
    feedbackTitle.value.trim().length > 0 &&
    feedbackDescription.value.trim().length > 0 &&
    !isSubmittingFeedback.value,
);

function handleScreenshotFiles(files: File[]) {
  const result = addScreenshotFiles(files);
  if (result.rejected > 0) {
    toasts.push({
      message: t("contact.feedback.form.screenshotLimit", {
        count: MAX_FEEDBACK_SCREENSHOT_COUNT,
      }),
      tone: "warning",
    });
  }
}

async function submitFeedback() {
  if (!canSubmitFeedback.value) return;

  isSubmittingFeedback.value = true;
  feedbackError.value = "";

  try {
    await createFeedback({
      feedback_type: feedbackType.value,
      page: feedbackPage.value,
      title: feedbackTitle.value,
      description: feedbackDescription.value,
      screenshots: feedbackScreenshots.value.map((item) => item.file),
    });

    feedbackTitle.value = "";
    feedbackDescription.value = "";
    clearScreenshots();
    toasts.push({ message: t("contact.feedback.form.success"), tone: "success" });
  } catch (err) {
    feedbackError.value = getBackendErrorMessage(err) || t("contact.feedback.form.failed");
  } finally {
    isSubmittingFeedback.value = false;
  }
}
</script>

<template>
  <AppPageShell :title="t('contact.title')" :show-back="false" :max-width="860">
    <div class="contactPage">
      <section class="contactSection">
        <h2 class="sectionTitle">{{ t("contact.sections.contact") }}</h2>

        <ContactMethodGrid v-if="methods.length" :methods="methods" />

        <section v-else class="emptyState">
          <h2>{{ t("contact.empty.title") }}</h2>
          <p>{{ t("contact.empty.description") }}</p>
        </section>
      </section>

      <section class="contactSection">
        <h2 class="sectionTitle">{{ t("contact.sections.feedback") }}</h2>

        <form class="feedbackForm" @submit.prevent="submitFeedback">
          <div class="formGrid">
            <label class="field">
              <span>{{ t("contact.feedback.form.type") }}</span>
              <BaseSelect
                :model-value="feedbackType"
                :options="feedbackTypeOptions"
                @update:model-value="feedbackType = $event as FeedbackType"
              />
            </label>

            <label class="field">
              <span>{{ t("contact.feedback.form.page") }}</span>
              <BaseSelect
                :model-value="feedbackPage"
                :options="feedbackPageOptions"
                @update:model-value="feedbackPage = $event as FeedbackPage"
              />
            </label>
          </div>

          <label class="field">
            <span>{{ t("contact.feedback.form.title") }}<span class="requiredMark">*</span></span>
            <input
              v-model="feedbackTitle"
              type="text"
              maxlength="160"
              :placeholder="t('contact.feedback.form.titlePlaceholder')"
            >
          </label>

          <label class="field">
            <span>{{ t("contact.feedback.form.description") }}<span class="requiredMark">*</span></span>
            <textarea
              v-model="feedbackDescription"
              rows="6"
              :placeholder="t('contact.feedback.form.descriptionPlaceholder')"
            />
          </label>

          <div class="field">
            <span>{{ t("contact.feedback.form.screenshot") }}</span>
            <ScreenshotUploadGrid
              :items="feedbackScreenshots"
              :max-count="MAX_FEEDBACK_SCREENSHOT_COUNT"
              :add-label="t('contact.feedback.form.screenshot')"
              :remove-label="t('common.cancel')"
              @files-selected="handleScreenshotFiles"
              @remove="removeScreenshot"
            />
          </div>

          <div v-if="feedbackError" class="formError">{{ feedbackError }}</div>

          <div class="formActions">
            <RouterLink
              v-if="auth.canManageFeedback"
              class="manageFeedbackLink"
              to="/feedback-admin"
            >
              {{ t("feedbackAdmin.title") }}
            </RouterLink>
            <BaseButton type="submit" variant="primary" :disabled="!canSubmitFeedback" :loading="isSubmittingFeedback">
              {{ t("contact.feedback.form.submit") }}
            </BaseButton>
          </div>
        </form>
      </section>
    </div>
  </AppPageShell>
</template>

<style scoped>
.contactPage {
  display: grid;
  gap: 24px;
}

.contactSection {
  display: grid;
  gap: 12px;
}

.sectionTitle {
  margin: 0;
  color: var(--c-text);
  font-size: 18px;
  line-height: 1.25;
}

.emptyState,
.feedbackForm {
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  background: var(--c-surface);
}

.emptyState h2,
.emptyState p {
  margin: 0;
}

.emptyState h2 {
  color: var(--c-text);
  font-size: 18px;
  line-height: 1.25;
}

.emptyState p {
  color: var(--c-text-muted);
  font-size: 14px;
  line-height: 1.6;
}

.emptyState {
  display: grid;
  gap: 8px;
  padding: 18px;
}

.feedbackForm {
  display: grid;
  gap: 14px;
  padding: 16px;
}

.formGrid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 7px;
  min-width: 0;
}

.field span {
  color: var(--c-text);
  font-size: 13px;
  font-weight: 600;
}

.field .requiredMark {
  margin-left: 3px;
  color: var(--c-danger);
}

.field input,
.field textarea {
  width: 100%;
  min-width: 0;
  border: 1px solid var(--c-border);
  border-radius: var(--r-2);
  background: var(--c-surface);
  color: var(--c-text);
  font: inherit;
}

.field input {
  height: 40px;
  padding: 0 12px;
}

.field :deep(.fieldRoot) {
  gap: 5px;
}

.field :deep(.trigger) {
  min-height: 40px;
  height: 40px;
  border-radius: 10px;
  padding: 0 12px;
}

.field :deep(.triggerLabel) {
  font-size: 13px;
}

.field textarea {
  resize: vertical;
  min-height: 132px;
  padding: 10px 12px;
  line-height: 1.5;
}

.formError {
  color: var(--c-danger);
  font-size: 13px;
}

.formActions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.manageFeedbackLink {
  color: var(--c-primary);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
}

.manageFeedbackLink:hover {
  text-decoration: underline;
}

.formActions :deep(button) {
  margin-left: auto;
}

@media (max-width: 560px) {
  .formGrid {
    grid-template-columns: 1fr;
  }
}
</style>
