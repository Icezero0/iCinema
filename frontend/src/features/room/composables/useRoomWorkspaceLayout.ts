import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import type { RoomPanelKey } from "@/features/room/types";

type UseRoomWorkspaceLayoutOptions = {
  activePanel: Ref<RoomPanelKey>;
  roomId: Ref<number | undefined>;
  isLoading: Ref<boolean>;
};

export function useRoomWorkspaceLayout(options: UseRoomWorkspaceLayoutOptions) {
  const { activePanel, roomId, isLoading } = options;

  const stageColumnEl = ref<HTMLElement | null>(null);
  const workspaceColumnEl = ref<HTMLElement | null>(null);
  const stageHeight = ref<number | null>(null);
  const stackedChatHeight = ref<number | null>(null);
  const viewportWidth = ref<number>(typeof window !== "undefined" ? window.innerWidth : 1440);

  let stageResizeObserver: ResizeObserver | null = null;
  let resizeRaf = 0;

  const isStackedLayout = computed(() => viewportWidth.value <= 720);

  const mainGridStyle = computed(() => {
    if (isStackedLayout.value || !stageHeight.value) {
      return undefined;
    }

    return {
      height: `${stageHeight.value}px`,
      minHeight: `${stageHeight.value}px`,
    };
  });

  const workspaceCardStyle = computed(() => {
    if (isStackedLayout.value) {
      return activePanel.value === "chat" && stackedChatHeight.value
        ? {
            height: `${stackedChatHeight.value}px`,
            maxHeight: `${stackedChatHeight.value}px`,
          }
        : undefined;
    }

    return stageHeight.value
      ? {
          height: "100%",
          maxHeight: "100%",
        }
      : undefined;
  });

  function syncWorkspaceHeight() {
    stageHeight.value = stageColumnEl.value
      ? Math.round(stageColumnEl.value.getBoundingClientRect().height)
      : null;

    if (!workspaceColumnEl.value || !isStackedLayout.value || activePanel.value !== "chat") {
      stackedChatHeight.value = null;
      return;
    }

    const workspaceRect = workspaceColumnEl.value.getBoundingClientRect();
    const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
    const offsetFromDocumentTop = workspaceRect.top + window.scrollY;
    const available = Math.floor(viewportHeight - offsetFromDocumentTop - 8);
    stackedChatHeight.value = Math.max(260, available);
  }

  function scheduleSyncWorkspaceHeight() {
    if (resizeRaf) {
      cancelAnimationFrame(resizeRaf);
    }

    resizeRaf = requestAnimationFrame(() => {
      syncWorkspaceHeight();
      resizeRaf = 0;
    });
  }

  function handleWindowResize() {
    viewportWidth.value = window.innerWidth;
    scheduleSyncWorkspaceHeight();
  }

  function setStageColumnEl(el: HTMLElement | null) {
    if (stageColumnEl.value === el) return;

    if (stageResizeObserver && stageColumnEl.value) {
      stageResizeObserver.unobserve(stageColumnEl.value);
    }

    stageColumnEl.value = el;

    if (stageResizeObserver && el) {
      stageResizeObserver.observe(el);
    }

    void nextTick(() => {
      scheduleSyncWorkspaceHeight();
    });
  }

  function setWorkspaceColumnEl(el: HTMLElement | null) {
    if (workspaceColumnEl.value === el) return;
    workspaceColumnEl.value = el;

    void nextTick(() => {
      scheduleSyncWorkspaceHeight();
    });
  }

  onMounted(() => {
    if (typeof ResizeObserver !== "undefined") {
      stageResizeObserver = new ResizeObserver(() => {
        scheduleSyncWorkspaceHeight();
      });

      if (stageColumnEl.value) {
        stageResizeObserver.observe(stageColumnEl.value);
      }
    }

    void nextTick(() => {
      scheduleSyncWorkspaceHeight();
    });

    window.addEventListener("resize", handleWindowResize, { passive: true });
  });

  onBeforeUnmount(() => {
    stageResizeObserver?.disconnect();
    window.removeEventListener("resize", handleWindowResize);

    if (resizeRaf) {
      cancelAnimationFrame(resizeRaf);
    }
  });

  watch(activePanel, () => {
    void nextTick(() => {
      scheduleSyncWorkspaceHeight();
    });
  });

  watch(
    () => [roomId.value, isLoading.value] as const,
    () => {
      void nextTick(() => {
        scheduleSyncWorkspaceHeight();
      });
    },
  );

  return {
    setStageColumnEl,
    setWorkspaceColumnEl,
    mainGridStyle,
    workspaceCardStyle,
  };
}
