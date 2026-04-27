<script setup lang="ts">
import { computed, ref, toRef } from "vue";
import ChatMessageItem from "./ChatMessageItem.vue";
import ChatComposer from "./ChatComposer.vue";
import { useChatTimelineScroll } from "@/features/chat/composables/useChatTimelineScroll";
import type { ChatMessage, ChatSegment } from "@/features/chat/types";

const props = defineProps<{
  roomKey?: number | string | null;
  messages: ChatMessage[];
  sendLabel?: string;
  selfAuthor?: string;
  loading?: boolean;
  sending?: boolean;
  loadingHistory?: boolean;
  hasOlder?: boolean;
  error?: string | null;
  loadingLabel?: string;
  emptyLabel?: string;
  sendMessage?: (segments: ChatSegment[]) => Promise<void> | void;
}>();
const emit = defineEmits<{
  send: [segments: ChatSegment[]];
  loadOlder: [];
}>();

const timelineRef = ref<HTMLElement | null>(null);
const timelineScroll = useChatTimelineScroll({
  timelineRef,
  roomKey: toRef(props, "roomKey"),
  messages: toRef(props, "messages"),
  loading: toRef(props, "loading"),
  loadingHistory: toRef(props, "loadingHistory"),
  sending: toRef(props, "sending"),
  hasOlder: toRef(props, "hasOlder"),
  onLoadOlder: () => emit("loadOlder"),
});

async function handleSend(segments: ChatSegment[]) {
  if (segments.length === 0) return;
  timelineScroll.markPendingSentMessage(props.messages.length + 1);

  if (props.sendMessage) {
    await props.sendMessage(segments);
    return;
  }

  emit("send", segments);
}

function getMessageGroupKey(message: ChatMessage) {
  if (typeof message.authorUserId === "number" && message.authorUserId > 0) {
    return `user:${message.authorUserId}`;
  }

  return `author:${message.author}|self:${message.self ? "1" : "0"}`;
}

const displayMessages = computed(() => props.messages.map((message, index, list) => {
  const previous = list[index - 1];
  const groupedWithPrevious =
    !!previous &&
    getMessageGroupKey(previous) === getMessageGroupKey(message);

  return {
    ...message,
    showAvatar: !groupedWithPrevious,
    showAuthor: !groupedWithPrevious,
  };
}));

</script>

<template>
  <div class="panel">
    <div ref="timelineRef" class="timeline" @scroll="timelineScroll.handleTimelineScroll">
      <div v-if="loading" class="feedback">
        <span class="feedbackText">{{ loadingLabel || "Loading…" }}</span>
      </div>
      <div v-else-if="error" class="feedback error">
        <span class="feedbackText">{{ error }}</span>
      </div>
      <div v-else-if="messages.length === 0" class="feedback">
        <span class="feedbackText">{{ emptyLabel || "No messages yet." }}</span>
      </div>
      <div
        v-for="message in displayMessages"
        :key="message.id"
        class="messageAnchor"
        :data-chat-message-id="String(message.id)"
      >
        <ChatMessageItem
          :author="message.author"
          :avatar-url="message.avatarUrl"
          :segments="message.segments"
          :self="message.self"
          :avatar-variant="message.avatarVariant"
          :role="message.role"
          :status="message.status"
          :show-avatar="message.showAvatar"
          :show-author="message.showAuthor"
        />
      </div>
    </div>

    <ChatComposer
      :send-label="sendLabel"
      :sending="sending"
      :send-message="handleSend"
      @send="handleSend"
    />
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
  padding-top: 8px;
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

.messageAnchor {
  min-width: 0;
}
</style>
