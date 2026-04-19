<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ChatMessageItem from "./ChatMessageItem.vue";
import ChatComposer from "./ChatComposer.vue";
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
}>();
const emit = defineEmits<{
  send: [segments: ChatSegment[]];
  loadOlder: [];
}>();

const timelineRef = ref<HTMLElement | null>(null);
const hasInitializedScroll = ref(false);
const pendingScrollToBottomAtCount = ref<number | null>(null);
const pendingHistoryAnchor = ref<{
  messageId: string;
  offsetTop: number;
  phase: "restoring" | "settling";
  stableFrames: number;
} | null>(null);
let timelineResizeObserver: ResizeObserver | null = null;
let removeTimelineLoadListener: (() => void) | null = null;
const shouldStickToBottom = ref(true);
let historyAnchorFrame = 0;

function getDistanceToBottom() {
  const timeline = timelineRef.value;
  if (!timeline) return Number.POSITIVE_INFINITY;

  return timeline.scrollHeight - timeline.clientHeight - timeline.scrollTop;
}

function cancelHistoryAnchorFrame() {
  if (!historyAnchorFrame) return;
  window.cancelAnimationFrame(historyAnchorFrame);
  historyAnchorFrame = 0;
}

function getMessageElement(messageId: string) {
  const timeline = timelineRef.value;
  if (!timeline) return null;

  return Array.from(
    timeline.querySelectorAll<HTMLElement>("[data-chat-message-id]"),
  ).find((element) => element.dataset.chatMessageId === messageId) ?? null;
}

function captureHistoryAnchor() {
  const timeline = timelineRef.value;
  if (!timeline) return null;

  const timelineRect = timeline.getBoundingClientRect();
  const messageElements = Array.from(
    timeline.querySelectorAll<HTMLElement>("[data-chat-message-id]"),
  );
  const unstableBoundaryMessageId =
    props.messages.length > 0 ? String(props.messages[0].id) : null;

  const firstVisibleElement = messageElements.find((element) => {
    const rect = element.getBoundingClientRect();
    return rect.bottom > timelineRect.top + 4;
  }) ?? messageElements[0];

  const anchorElement =
    unstableBoundaryMessageId &&
    firstVisibleElement?.dataset.chatMessageId === unstableBoundaryMessageId
      ? messageElements.find((element) => (
        element.dataset.chatMessageId !== unstableBoundaryMessageId &&
        element.getBoundingClientRect().bottom > timelineRect.top + 4
      )) ??
        messageElements.find((element) => (
          element.dataset.chatMessageId !== unstableBoundaryMessageId
        )) ??
        firstVisibleElement
      : firstVisibleElement;

  if (!anchorElement) return null;

  return {
    messageId: anchorElement.dataset.chatMessageId ?? "",
    offsetTop: anchorElement.getBoundingClientRect().top - timelineRect.top,
    phase: "restoring" as const,
    stableFrames: 0,
  };
}

function restoreHistoryAnchor() {
  const timeline = timelineRef.value;
  const historyAnchor = pendingHistoryAnchor.value;
  if (!timeline || !historyAnchor?.messageId) return false;

  const anchorElement = getMessageElement(historyAnchor.messageId);
  if (!anchorElement) {
    pendingHistoryAnchor.value = null;
    return false;
  }

  const timelineRect = timeline.getBoundingClientRect();
  const currentOffset = anchorElement.getBoundingClientRect().top - timelineRect.top;
  const delta = currentOffset - historyAnchor.offsetTop;

  if (Math.abs(delta) < 0.5) {
    historyAnchor.phase = "settling";
    historyAnchor.stableFrames += 1;
    return false;
  }

  timeline.scrollTop += delta;
  historyAnchor.phase = "restoring";
  historyAnchor.stableFrames = 0;
  return true;
}

function settleHistoryAnchor() {
  cancelHistoryAnchorFrame();

  historyAnchorFrame = window.requestAnimationFrame(() => {
    historyAnchorFrame = 0;

    const historyAnchor = pendingHistoryAnchor.value;
    if (!historyAnchor || props.loadingHistory) return;

    const corrected = restoreHistoryAnchor();
    if (corrected) {
      settleHistoryAnchor();
      return;
    }

    if (historyAnchor.stableFrames >= 2) {
      pendingHistoryAnchor.value = null;
      return;
    }

    settleHistoryAnchor();
  });
}

function handleSend(segments: ChatSegment[]) {
  if (segments.length === 0) return;
  pendingScrollToBottomAtCount.value = props.messages.length + 1;
  emit("send", segments);
}

function scrollToBottom() {
  const timeline = timelineRef.value;
  if (!timeline) return;
  timeline.scrollTop = timeline.scrollHeight;
  shouldStickToBottom.value = true;
}

function handleTimelineScroll() {
  const timeline = timelineRef.value;
  if (!timeline) return;

  shouldStickToBottom.value = getDistanceToBottom() <= 24;

  if (
    timeline.scrollTop <= 4 &&
    props.hasOlder &&
    !props.loading &&
    !props.loadingHistory &&
    !pendingHistoryAnchor.value
  ) {
    cancelHistoryAnchorFrame();
    pendingHistoryAnchor.value = captureHistoryAnchor();
    emit("loadOlder");
  }
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

onMounted(() => {
  const timeline = timelineRef.value;

  if (typeof ResizeObserver !== "undefined" && timeline) {
    timelineResizeObserver = new ResizeObserver(() => {
      if (pendingHistoryAnchor.value && !props.loadingHistory) {
        void nextTick().then(() => {
          settleHistoryAnchor();
        });
        return;
      }

      if (shouldStickToBottom.value) {
        void nextTick().then(() => {
          scrollToBottom();
        });
      }
    });
    timelineResizeObserver.observe(timeline);
  }

  if (timeline) {
    const onTimelineMediaLoad = (event: Event) => {
      const target = event.target;
      if (!(target instanceof HTMLImageElement)) return;
      if (!timeline.contains(target)) return;

      if (pendingHistoryAnchor.value && !props.loadingHistory) {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            settleHistoryAnchor();
          });
        });
        return;
      }

      if (!shouldStickToBottom.value) return;

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          scrollToBottom();
        });
      });
    };

    timeline.addEventListener("load", onTimelineMediaLoad, true);
    removeTimelineLoadListener = () => {
      timeline.removeEventListener("load", onTimelineMediaLoad, true);
      removeTimelineLoadListener = null;
    };
  }
});

onBeforeUnmount(() => {
  timelineResizeObserver?.disconnect();
  timelineResizeObserver = null;
  removeTimelineLoadListener?.();
  cancelHistoryAnchorFrame();
});

watch(
  () => props.roomKey,
  () => {
    hasInitializedScroll.value = false;
    pendingScrollToBottomAtCount.value = null;
    pendingHistoryAnchor.value = null;
    shouldStickToBottom.value = true;
    cancelHistoryAnchorFrame();
  },
);

watch(
  () => [props.loading, props.messages.length] as const,
  async ([loading, messageCount]) => {
    if (loading || hasInitializedScroll.value || messageCount === 0) return;

    await nextTick();
    scrollToBottom();
    hasInitializedScroll.value = true;
  },
  { immediate: true },
);

watch(
  () => props.messages.length,
  async (nextLength, previousLength) => {
    if (nextLength === previousLength) return;

    await nextTick();

    const timeline = timelineRef.value;
    if (!timeline) return;

    if (pendingHistoryAnchor.value) {
      settleHistoryAnchor();
      return;
    }

    if (
      pendingScrollToBottomAtCount.value != null &&
      nextLength >= pendingScrollToBottomAtCount.value
    ) {
      scrollToBottom();
      pendingScrollToBottomAtCount.value = null;
    }
  },
);

watch(
  () => props.loadingHistory,
  async (loadingHistory) => {
    if (loadingHistory || !pendingHistoryAnchor.value) return;

    await nextTick();

    settleHistoryAnchor();
  },
);

watch(
  () => props.sending,
  (sending) => {
    if (!sending && pendingScrollToBottomAtCount.value != null) {
      if (props.messages.length < pendingScrollToBottomAtCount.value) {
        pendingScrollToBottomAtCount.value = null;
      }
    }
  },
);
</script>

<template>
  <div class="panel">
    <div ref="timelineRef" class="timeline" @scroll="handleTimelineScroll">
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
