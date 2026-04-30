<script setup lang="ts">
import { computed, ref, toRef } from "vue";
import { useI18n } from "vue-i18n";
import ChatMessageItem from "./ChatMessageItem.vue";
import ChatComposer from "./ChatComposer.vue";
import { useChatTimelineScroll } from "@/features/chat/composables/useChatTimelineScroll";
import type { ChatMessage, ChatSegment } from "@/features/chat/types";
import type { MemberStatus } from "@/features/room/types";

const props = defineProps<{
  roomKey?: number | string | null;
  active?: boolean;
  messages: ChatMessage[];
  sendLabel?: string;
  loading?: boolean;
  sending?: boolean;
  loadingHistory?: boolean;
  hasOlder?: boolean;
  error?: string | null;
  loadingLabel?: string;
  emptyLabel?: string;
  sendMessage?: (segments: ChatSegment[]) => Promise<void> | void;
  captureScreenshot?: () => Promise<void> | void;
  memberStatusByUserId?: Map<number, MemberStatus>;
}>();
const emit = defineEmits<{
  send: [segments: ChatSegment[]];
  loadOlder: [];
}>();
const { t } = useI18n();

const timelineRef = ref<HTMLElement | null>(null);
const timelineScroll = useChatTimelineScroll({
  timelineRef,
  roomKey: toRef(props, "roomKey"),
  active: toRef(props, "active"),
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

function getMessageStatus(message: ChatMessage) {
  if (typeof message.authorUserId !== "number") {
    return message.status ?? "offline";
  }

  return props.memberStatusByUserId?.get(message.authorUserId) ?? message.status ?? "offline";
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
const newMessagesBelowCount = computed(() => timelineScroll.newMessagesBelowCount.value);
const newMessagesLabel = computed(() =>
  t("chat.newMessagesBelow", { count: newMessagesBelowCount.value }));

</script>

<template>
  <div class="panel">
    <div class="timelineWrap">
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
            :status="getMessageStatus(message)"
            :show-avatar="message.showAvatar"
            :show-author="message.showAuthor"
          />
        </div>
      </div>

      <Transition name="new-message-badge">
        <button
          v-if="newMessagesBelowCount > 0"
          class="newMessagesBadge"
          type="button"
          @click="timelineScroll.scrollToLatestMessages"
        >
          {{ newMessagesLabel }}
        </button>
      </Transition>
    </div>

    <ChatComposer
      :send-label="sendLabel"
      :sending="sending"
      :send-message="handleSend"
      :capture-screenshot="captureScreenshot"
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
  position: relative;
}

.timelineWrap {
  min-height: 0;
  position: relative;
  display: grid;
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

.newMessagesBadge {
  position: absolute;
  left: 50%;
  bottom: 12px;
  transform: translateX(-50%);
  min-height: 30px;
  max-width: min(220px, calc(100% - 32px));
  padding: 6px 12px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 28%, var(--c-border));
  border-radius: 999px;
  background: color-mix(in srgb, var(--c-primary) 12%, var(--c-surface));
  color: var(--c-text);
  box-shadow: 0 12px 28px rgb(0 0 0 / 0.14);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  z-index: 2;
}

.newMessagesBadge:hover {
  background: color-mix(in srgb, var(--c-primary) 18%, var(--c-surface));
}

.new-message-badge-enter-active,
.new-message-badge-leave-active {
  transition: opacity 140ms ease, transform 160ms ease;
}

.new-message-badge-enter-from,
.new-message-badge-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(6px);
}
</style>
