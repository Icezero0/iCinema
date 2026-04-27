import { nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import type { ChatMessage } from "@/features/chat/types";

const BOTTOM_STICKY_THRESHOLD_PX = 24;
const LOAD_OLDER_SCROLL_TOP_THRESHOLD_PX = 4;
const HISTORY_ANCHOR_STABLE_DELTA_PX = 0.5;
const HISTORY_ANCHOR_STABLE_FRAMES = 2;
const INITIAL_SCROLL_SETTLE_MS = 800;

type HistoryAnchor = {
  messageId: string;
  offsetTop: number;
  phase: "restoring" | "settling";
  stableFrames: number;
};

type UseChatTimelineScrollOptions = {
  timelineRef: Ref<HTMLElement | null>;
  roomKey: Ref<number | string | null | undefined>;
  messages: Ref<ChatMessage[]>;
  loading: Ref<boolean | undefined>;
  loadingHistory: Ref<boolean | undefined>;
  sending: Ref<boolean | undefined>;
  hasOlder: Ref<boolean | undefined>;
  onLoadOlder: () => void;
};

export function useChatTimelineScroll(options: UseChatTimelineScrollOptions) {
  const {
    timelineRef,
    roomKey,
    messages,
    loading,
    loadingHistory,
    sending,
    hasOlder,
    onLoadOlder,
  } = options;

  const hasInitializedScroll = ref(false);
  const pendingScrollToBottomAtCount = ref<number | null>(null);
  const pendingHistoryAnchor = ref<HistoryAnchor | null>(null);
  const isInitialScrollSettling = ref(false);
  const shouldStickToBottom = ref(true);

  let timelineResizeObserver: ResizeObserver | null = null;
  let removeTimelineLoadListener: (() => void) | null = null;
  let removeInitialScrollInteractionListeners: (() => void) | null = null;
  let historyAnchorFrame = 0;
  let initialScrollSettlingTimer = 0;

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

  function clearInitialScrollSettlingTimer() {
    if (!initialScrollSettlingTimer) return;
    window.clearTimeout(initialScrollSettlingTimer);
    initialScrollSettlingTimer = 0;
  }

  function scheduleInitialScrollSettling() {
    isInitialScrollSettling.value = true;
    clearInitialScrollSettlingTimer();
    initialScrollSettlingTimer = window.setTimeout(() => {
      initialScrollSettlingTimer = 0;
      isInitialScrollSettling.value = false;
    }, INITIAL_SCROLL_SETTLE_MS);
  }

  function cancelInitialScrollSettling() {
    if (!isInitialScrollSettling.value) return;

    clearInitialScrollSettlingTimer();
    isInitialScrollSettling.value = false;
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
    const firstMessage = messages.value[0];
    const unstableBoundaryMessageId = firstMessage ? String(firstMessage.id) : null;

    const firstVisibleElement = messageElements.find((element) => {
      const rect = element.getBoundingClientRect();
      return rect.bottom > timelineRect.top + LOAD_OLDER_SCROLL_TOP_THRESHOLD_PX;
    }) ?? messageElements[0];

    const anchorElement =
      unstableBoundaryMessageId &&
      firstVisibleElement?.dataset.chatMessageId === unstableBoundaryMessageId
        ? messageElements.find((element) => (
          element.dataset.chatMessageId !== unstableBoundaryMessageId &&
          element.getBoundingClientRect().bottom >
            timelineRect.top + LOAD_OLDER_SCROLL_TOP_THRESHOLD_PX
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

    if (Math.abs(delta) < HISTORY_ANCHOR_STABLE_DELTA_PX) {
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
      if (!historyAnchor || loadingHistory.value) return;

      const corrected = restoreHistoryAnchor();
      if (corrected) {
        settleHistoryAnchor();
        return;
      }

      if (historyAnchor.stableFrames >= HISTORY_ANCHOR_STABLE_FRAMES) {
        pendingHistoryAnchor.value = null;
        return;
      }

      settleHistoryAnchor();
    });
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

    if (isInitialScrollSettling.value) {
      shouldStickToBottom.value = true;
      return;
    }

    shouldStickToBottom.value = getDistanceToBottom() <= BOTTOM_STICKY_THRESHOLD_PX;

    if (
      timeline.scrollTop <= LOAD_OLDER_SCROLL_TOP_THRESHOLD_PX &&
      hasOlder.value &&
      !loading.value &&
      !loadingHistory.value &&
      !pendingHistoryAnchor.value
    ) {
      cancelHistoryAnchorFrame();
      pendingHistoryAnchor.value = captureHistoryAnchor();
      onLoadOlder();
    }
  }

  function markPendingSentMessage(expectedMessageCount: number) {
    pendingScrollToBottomAtCount.value = expectedMessageCount;
  }

  onMounted(() => {
    const timeline = timelineRef.value;

    if (typeof ResizeObserver !== "undefined" && timeline) {
      timelineResizeObserver = new ResizeObserver(() => {
        if (pendingHistoryAnchor.value && !loadingHistory.value) {
          void nextTick().then(() => {
            settleHistoryAnchor();
          });
          return;
        }

        if (shouldStickToBottom.value || isInitialScrollSettling.value) {
          if (isInitialScrollSettling.value) {
            scheduleInitialScrollSettling();
          }
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

        if (pendingHistoryAnchor.value && !loadingHistory.value) {
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              settleHistoryAnchor();
            });
          });
          return;
        }

        if (!shouldStickToBottom.value && !isInitialScrollSettling.value) return;

        if (isInitialScrollSettling.value) {
          scheduleInitialScrollSettling();
        }

        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            scrollToBottom();
          });
        });
      };

      const cancelInitialScrollSettlingOnWheel = () => cancelInitialScrollSettling();
      const cancelInitialScrollSettlingOnTouchStart = () => cancelInitialScrollSettling();
      const cancelInitialScrollSettlingOnPointerDown = () => cancelInitialScrollSettling();

      timeline.addEventListener("load", onTimelineMediaLoad, true);
      timeline.addEventListener("wheel", cancelInitialScrollSettlingOnWheel, { passive: true });
      timeline.addEventListener("touchstart", cancelInitialScrollSettlingOnTouchStart, { passive: true });
      timeline.addEventListener("pointerdown", cancelInitialScrollSettlingOnPointerDown, { passive: true });
      removeTimelineLoadListener = () => {
        timeline.removeEventListener("load", onTimelineMediaLoad, true);
        removeTimelineLoadListener = null;
      };
      removeInitialScrollInteractionListeners = () => {
        timeline.removeEventListener("wheel", cancelInitialScrollSettlingOnWheel);
        timeline.removeEventListener("touchstart", cancelInitialScrollSettlingOnTouchStart);
        timeline.removeEventListener("pointerdown", cancelInitialScrollSettlingOnPointerDown);
        removeInitialScrollInteractionListeners = null;
      };
    }
  });

  onBeforeUnmount(() => {
    clearInitialScrollSettlingTimer();
    timelineResizeObserver?.disconnect();
    timelineResizeObserver = null;
    removeTimelineLoadListener?.();
    removeInitialScrollInteractionListeners?.();
    cancelHistoryAnchorFrame();
  });

  watch(
    roomKey,
    () => {
      hasInitializedScroll.value = false;
      pendingScrollToBottomAtCount.value = null;
      pendingHistoryAnchor.value = null;
      isInitialScrollSettling.value = false;
      clearInitialScrollSettlingTimer();
      shouldStickToBottom.value = true;
      cancelHistoryAnchorFrame();
    },
  );

  watch(
    () => [loading.value, messages.value.length] as const,
    async ([isLoading, messageCount]) => {
      if (isLoading || hasInitializedScroll.value || messageCount === 0) return;

      await nextTick();
      scrollToBottom();
      hasInitializedScroll.value = true;
      scheduleInitialScrollSettling();
    },
    { immediate: true },
  );

  watch(
    () => messages.value.length,
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
    loadingHistory,
    async (isLoadingHistory) => {
      if (isLoadingHistory || !pendingHistoryAnchor.value) return;

      await nextTick();
      settleHistoryAnchor();
    },
  );

  watch(
    sending,
    (isSending) => {
      if (!isSending && pendingScrollToBottomAtCount.value != null) {
        if (messages.value.length < pendingScrollToBottomAtCount.value) {
          pendingScrollToBottomAtCount.value = null;
        }
      }
    },
  );

  return {
    handleTimelineScroll,
    markPendingSentMessage,
  };
}
