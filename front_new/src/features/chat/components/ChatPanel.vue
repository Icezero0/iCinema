<script setup lang="ts">
import { CameraIcon, FaceSmileIcon, PaperAirplaneIcon } from "@heroicons/vue/24/outline";
import { useI18n } from "vue-i18n";
import AppIcon from "@/ui/base/AppIcon.vue";
import ChatMessageItem from "./ChatMessageItem.vue";
import type { ChatMessage } from "@/features/chat/types";

const { t } = useI18n();

defineProps<{
  messages: ChatMessage[];
  sendLabel?: string;
}>();
</script>

<template>
  <div class="panel">
    <div class="timeline">
      <ChatMessageItem
        v-for="message in messages"
        :key="message.id"
        :author="message.author"
        :sections="message.sections"
        :self="message.self"
        :avatar-variant="message.avatarVariant"
        :role="message.role"
        :status="message.status"
      />
    </div>

    <div class="composer">
      <div class="toolbar">
        <BaseIconButton class="toolButton" :aria-label="t('chat.toolbar.emoji')">
          <AppIcon :icon="FaceSmileIcon" :size="16" />
        </BaseIconButton>
        <BaseIconButton class="toolButton" :aria-label="t('chat.toolbar.screenshot')">
          <AppIcon :icon="CameraIcon" :size="16" />
        </BaseIconButton>
      </div>

      <div class="inputRow">
        <div class="field" />
        <BaseIconButton class="sendButton" :aria-label="sendLabel || 'Send'">
          <AppIcon :icon="PaperAirplaneIcon" :size="16" />
        </BaseIconButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panel {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 6px;
  min-height: 0;
}

.timeline {
  display: grid;
  gap: 10px;
  padding-bottom: 6px;
  padding-left: 6px;
  padding-right: 6px;
  margin-left: -14px;
  margin-right: -14px;
  border-bottom: 1px solid var(--c-border);
  min-height: 0;
  overflow: auto;
}

.composer {
  display: grid;
  gap: 6px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  margin-top: -2px;
}

.toolButton {
  width: 28px;
  height: 28px;
  min-width: 28px;
  opacity: 0.82;
  border-radius: 10px;
}

.inputRow {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

.field {
  min-height: 44px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  display: flex;
  align-items: center;
}

.sendButton {
  width: 44px;
  min-width: 44px;
  background: color-mix(in srgb, var(--c-primary) 8%, var(--c-surface));
  color: var(--c-primary);
  border-radius: 14px;
}

.sendButton:hover {
  background: color-mix(in srgb, var(--c-primary) 12%, var(--c-surface));
}

</style>
