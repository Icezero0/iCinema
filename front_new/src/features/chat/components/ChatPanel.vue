<script setup lang="ts">
import ChatMessageItem from "./ChatMessageItem.vue";
import ChatComposer from "./ChatComposer.vue";
import type { ChatMessage, ChatSegment } from "@/features/chat/types";

const props = defineProps<{
  messages: ChatMessage[];
  sendLabel?: string;
  selfAuthor?: string;
  loading?: boolean;
  sending?: boolean;
  error?: string | null;
  loadingLabel?: string;
  emptyLabel?: string;
}>();
const emit = defineEmits<{
  send: [segments: ChatSegment[]];
}>();

function handleSend(segments: ChatSegment[]) {
  if (segments.length === 0) return;
  emit("send", segments);
}
</script>

<template>
  <div class="panel">
    <div class="timeline">
      <div v-if="loading" class="feedback">
        <span class="feedbackText">{{ loadingLabel || "Loading…" }}</span>
      </div>
      <div v-else-if="error" class="feedback error">
        <span class="feedbackText">{{ error }}</span>
      </div>
      <div v-else-if="messages.length === 0" class="feedback">
        <span class="feedbackText">{{ emptyLabel || "No messages yet." }}</span>
      </div>
      <ChatMessageItem
        v-for="message in messages"
        :key="message.id"
        :author="message.author"
        :avatar-url="message.avatarUrl"
        :segments="message.segments"
        :self="message.self"
        :avatar-variant="message.avatarVariant"
        :role="message.role"
        :status="message.status"
      />
    </div>

    <ChatComposer :send-label="sendLabel" @send="handleSend" />
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
  align-content: start;
  padding-bottom: 6px;
  padding-left: 6px;
  padding-right: 6px;
  margin-left: -14px;
  margin-right: -14px;
  border-bottom: 1px solid var(--c-border);
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
}

.feedback {
  min-height: 100%;
  display: grid;
  place-items: center;
  color: var(--c-text-muted);
  font-size: 13px;
  text-align: center;
}

.feedback.error {
  color: var(--c-danger);
}

.feedbackText {
  padding: 14px;
}
</style>
