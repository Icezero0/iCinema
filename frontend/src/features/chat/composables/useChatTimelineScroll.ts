import { nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import type { ChatMessage } from "@/features/chat/types";

const BOTTOM_STICKY_THRESHOLD_PX = 24;
const LOAD_OLDER_SCROLL_TOP_THRESHOLD_PX = 4;
const HISTORY_ANCHOR_STABLE_DELTA_PX = 0.5;
const HISTORY_ANCHOR_STABLE_FRAMES = 2;
const HISTORY_ANCHOR_MAX_FRAMES = 36;
const INITIAL_SCROLL_SETTLE_MS = 800;
const NEW_MESSAGE_SEEN_RATIO = 0.5;
const USER_SCROLL_INTENT_MS = 1200;

type HistoryAnchor = {
  messageId: string;
  offsetTop: number;
  phase: "restoring" | "settling";
  stableFrames: number;
  frameCount: number;
};

type ViewportAnchor = {
  messageId: string;
  offsetTop: number;
  scrollTop: number;
  stickToBottom: boolean;
};

type UseChatTimelineScrollOptions = {
  timelineRef: Ref<HTMLElement | null>;
  roomKey: Ref<number | string | null | undefined>;
  active: Ref<boolean | undefined>;
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
    active,
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
  const newMessagesBelowCount = ref(0);
  const unseenNewMessageIds = ref<string[]>([]);

  let timelineResizeObserver: ResizeObserver | null = null;
  let removeTimelineLoadListener: (() => void) | null = null;
  let removeInitialScrollInteractionListeners: (() => void) | null = null;
  let historyAnchorFrame = 0;
  let initialScrollSettlingTimer = 0;
  let lastUserScrollIntentAt = 0;
  let suppressLoadOlderUntilUserIntent = false;
  let lastVisibleViewportAnchor: ViewportAnchor | null = null;
  let shouldRestoreViewportAfterInactive = false;

  function isTimelineMeasurable(timeline: HTMLElement | null): timeline is HTMLElement {
    if (!timeline || !timeline.isConnected) return false;
    const rect = timeline.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && timeline.clientHeight > 0;
  }

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

  function clearPendingHistoryAnchor() {
    pendingHistoryAnchor.value = null;
    cancelHistoryAnchorFrame();
  }

  function markUserScrollIntent() {
    lastUserScrollIntentAt = Date.now();
    suppressLoadOlderUntilUserIntent = false;
    if (pendingHistoryAnchor.value && !loadingHistory.value) {
      clearPendingHistoryAnchor();
    }
  }

  function hasRecentUserScrollIntent() {
    return Date.now() - lastUserScrollIntentAt <= USER_SCROLL_INTENT_MS;
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

  function captureViewportAnchor() {
    const timeline = timelineRef.value;
    if (!isTimelineMeasurable(timeline)) return null;

    const timelineRect = timeline.getBoundingClientRect();
    const firstVisibleElement = Array.from(
      timeline.querySelectorAll<HTMLElement>("[data-chat-message-id]"),
    ).find((element) => {
      const rect = element.getBoundingClientRect();
      return rect.bottom > timelineRect.top + LOAD_OLDER_SCROLL_TOP_THRESHOLD_PX;
    });

    if (!firstVisibleElement?.dataset.chatMessageId) return null;

    return {
      messageId: firstVisibleElement.dataset.chatMessageId,
      offsetTop: firstVisibleElement.getBoundingClientRect().top - timelineRect.top,
      scrollTop: timeline.scrollTop,
      stickToBottom: shouldStickToBottom.value,
    } satisfies ViewportAnchor;
  }

  function rememberVisibleViewportAnchor() {
    const anchor = captureViewportAnchor();
    if (anchor) {
      lastVisibleViewportAnchor = anchor;
    }
  }

  function restoreViewportAnchor(anchor: ViewportAnchor) {
    const timeline = timelineRef.value;
    if (!isTimelineMeasurable(timeline)) return;

    if (anchor.stickToBottom) {
      scrollToBottom();
      return;
    }

    const anchorElement = getMessageElement(anchor.messageId);
    if (!anchorElement) {
      timeline.scrollTop = anchor.scrollTop;
    } else {
      const timelineRect = timeline.getBoundingClientRect();
      const currentOffset = anchorElement.getBoundingClientRect().top - timelineRect.top;
      timeline.scrollTop += currentOffset - anchor.offsetTop;
    }

    shouldStickToBottom.value = getDistanceToBottom() <= BOTTOM_STICKY_THRESHOLD_PX;
    pruneVisibleNewMessages();
  }

  function restoreViewportAfterInactiveIfNeeded() {
    if (!shouldRestoreViewportAfterInactive || !lastVisibleViewportAnchor) return;
    if (!isTimelineMeasurable(timelineRef.value)) return;

    const anchor = lastVisibleViewportAnchor;
    shouldRestoreViewportAfterInactive = false;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        restoreViewportAnchor(anchor);
        rememberVisibleViewportAnchor();
      });
    });
  }

  function setUnseenNewMessageIds(messageIds: string[]) {
    unseenNewMessageIds.value = Array.from(new Set(messageIds));
    newMessagesBelowCount.value = unseenNewMessageIds.value.length;
  }

  function resetUnseenNewMessages() {
    setUnseenNewMessageIds([]);
  }

  function pruneVisibleNewMessages() {
    const timeline = timelineRef.value;
    if (!timeline || unseenNewMessageIds.value.length === 0) return;

    const timelineRect = timeline.getBoundingClientRect();
    const remainingIds = unseenNewMessageIds.value.filter((messageId) => {
      const element = getMessageElement(messageId);
      if (!element) return false;

      const rect = element.getBoundingClientRect();
      const visibleHeight =
        Math.min(rect.bottom, timelineRect.bottom) -
        Math.max(rect.top, timelineRect.top);
      const elementHeight = Math.max(1, rect.height);
      const isSeen = visibleHeight / elementHeight >= NEW_MESSAGE_SEEN_RATIO;

      return !isSeen;
    });

    setUnseenNewMessageIds(remainingIds);
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
      frameCount: 0,
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
      historyAnchor.frameCount += 1;

      const corrected = restoreHistoryAnchor();
      if (corrected) {
        if (historyAnchor.frameCount >= HISTORY_ANCHOR_MAX_FRAMES) {
          pendingHistoryAnchor.value = null;
          return;
        }
        settleHistoryAnchor();
        return;
      }

      if (
        historyAnchor.stableFrames >= HISTORY_ANCHOR_STABLE_FRAMES ||
        historyAnchor.frameCount >= HISTORY_ANCHOR_MAX_FRAMES
      ) {
        pendingHistoryAnchor.value = null;
        return;
      }

      settleHistoryAnchor();
    });
  }

  function scrollToBottom() {
    const timeline = timelineRef.value;
    if (!timeline) return;
    if (!isTimelineMeasurable(timeline)) return;
    timeline.scrollTop = timeline.scrollHeight;
    shouldStickToBottom.value = true;
    resetUnseenNewMessages();
    rememberVisibleViewportAnchor();
  }

  function scrollToLatestMessages() {
    void nextTick().then(() => {
      scrollToBottom();
    });
  }

  function handleTimelineScroll() {
    const timeline = timelineRef.value;
    if (!timeline) return;

    if (active.value === false || !isTimelineMeasurable(timeline)) {
      return;
    }

    if (shouldRestoreViewportAfterInactive) {
      restoreViewportAfterInactiveIfNeeded();
      return;
    }

    if (isInitialScrollSettling.value) {
      shouldStickToBottom.value = true;
      rememberVisibleViewportAnchor();
      return;
    }

    shouldStickToBottom.value = getDistanceToBottom() <= BOTTOM_STICKY_THRESHOLD_PX;
    rememberVisibleViewportAnchor();
    if (shouldStickToBottom.value) {
      resetUnseenNewMessages();
    } else {
      pruneVisibleNewMessages();
    }

    if (
      timeline.scrollTop <= LOAD_OLDER_SCROLL_TOP_THRESHOLD_PX &&
      hasOlder.value &&
      !loading.value &&
      !loadingHistory.value &&
      !pendingHistoryAnchor.value &&
      !suppressLoadOlderUntilUserIntent &&
      hasRecentUserScrollIntent()
    ) {
      cancelHistoryAnchorFrame();
      pendingHistoryAnchor.value = captureHistoryAnchor();
      if (pendingHistoryAnchor.value) {
        onLoadOlder();
      }
    }
  }

  function markPendingSentMessage(expectedMessageCount: number) {
    pendingScrollToBottomAtCount.value = expectedMessageCount;
  }

  onMounted(() => {
    const timeline = timelineRef.value;

    if (typeof ResizeObserver !== "undefined" && timeline) {
      timelineResizeObserver = new ResizeObserver(() => {
        if (active.value === false || !isTimelineMeasurable(timeline)) {
          return;
        }

        if (shouldRestoreViewportAfterInactive) {
          restoreViewportAfterInactiveIfNeeded();
          return;
        }

        if (pendingHistoryAnchor.value && !loadingHistory.value) {
          void nextTick().then(() => {
            settleHistoryAnchor();
          });
          return;
        }

        void nextTick().then(() => {
          pruneVisibleNewMessages();
          rememberVisibleViewportAnchor();
        });

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

        if (!shouldStickToBottom.value && !isInitialScrollSettling.value) {
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              pruneVisibleNewMessages();
            });
          });
          return;
        }

        if (isInitialScrollSettling.value) {
          scheduleInitialScrollSettling();
        }

        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            scrollToBottom();
          });
        });
      };

      const handleUserScrollIntent = () => {
        markUserScrollIntent();
        cancelInitialScrollSettling();
      };

      timeline.addEventListener("load", onTimelineMediaLoad, true);
      timeline.addEventListener("wheel", handleUserScrollIntent, { passive: true });
      timeline.addEventListener("touchstart", handleUserScrollIntent, { passive: true });
      timeline.addEventListener("pointerdown", handleUserScrollIntent, { passive: true });
      removeTimelineLoadListener = () => {
        timeline.removeEventListener("load", onTimelineMediaLoad, true);
        removeTimelineLoadListener = null;
      };
      removeInitialScrollInteractionListeners = () => {
        timeline.removeEventListener("wheel", handleUserScrollIntent);
        timeline.removeEventListener("touchstart", handleUserScrollIntent);
        timeline.removeEventListener("pointerdown", handleUserScrollIntent);
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
      clearPendingHistoryAnchor();
      isInitialScrollSettling.value = false;
      resetUnseenNewMessages();
      clearInitialScrollSettlingTimer();
      shouldStickToBottom.value = true;
      lastVisibleViewportAnchor = null;
      shouldRestoreViewportAfterInactive = false;
      suppressLoadOlderUntilUserIntent = false;
      lastUserScrollIntentAt = 0;
      cancelHistoryAnchorFrame();
    },
  );

  watch(
    active,
    async (isActive, wasActive) => {
      if (isActive === false) {
        rememberVisibleViewportAnchor();
        shouldRestoreViewportAfterInactive = true;
        suppressLoadOlderUntilUserIntent = true;
        lastUserScrollIntentAt = 0;
        return;
      }

      if (isActive && wasActive === false) {
        suppressLoadOlderUntilUserIntent = true;
        lastUserScrollIntentAt = 0;
        await nextTick();
        restoreViewportAfterInactiveIfNeeded();
      }
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
    () => messages.value.map((message) => String(message.id)),
    async (nextIds, previousIds) => {
      if (nextIds.length === previousIds.length) return;

      await nextTick();

      const timeline = timelineRef.value;
      if (!timeline) return;

      if (pendingHistoryAnchor.value) {
        settleHistoryAnchor();
        return;
      }

      if (
        pendingScrollToBottomAtCount.value != null &&
        nextIds.length >= pendingScrollToBottomAtCount.value
      ) {
        scrollToBottom();
        pendingScrollToBottomAtCount.value = null;
        return;
      }

      if (nextIds.length > previousIds.length) {
        if (!hasInitializedScroll.value) return;

        if (shouldStickToBottom.value) {
          scrollToBottom();
          return;
        }

        const previousIdSet = new Set(previousIds);
        const appendedMessageIds = nextIds.filter((id) => !previousIdSet.has(id));
        setUnseenNewMessageIds([
          ...unseenNewMessageIds.value,
          ...appendedMessageIds,
        ]);
        pruneVisibleNewMessages();
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
    newMessagesBelowCount,
    scrollToLatestMessages,
  };
}
