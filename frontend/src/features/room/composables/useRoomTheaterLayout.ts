import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from "vue";
import {
  readPersistedState,
  writePersistedState,
} from "@/stores/persistence";

const DEFAULT_WORKSPACE_WIDTH = 380;
const MIN_WORKSPACE_WIDTH = 300;
const MAX_WORKSPACE_WIDTH = 560;
const THEATER_PADDING = 16;
const THEATER_BODY_CLASS = "icinema-room-theater-active";

function theaterWorkspaceWidthStorageKey(roomId: number) {
  return `icinema:room:${roomId}:theaterWorkspaceWidth`;
}

function clampWorkspaceWidth(value: number) {
  const viewportWidth = typeof window === "undefined" ? 1440 : window.innerWidth;
  const dynamicMax = Math.min(MAX_WORKSPACE_WIDTH, Math.floor(viewportWidth * 0.46));
  const maxWidth = Math.max(MIN_WORKSPACE_WIDTH, dynamicMax);
  return Math.min(maxWidth, Math.max(MIN_WORKSPACE_WIDTH, Math.round(value)));
}

export function useRoomTheaterLayout(roomId: Ref<number>) {
  const isTheaterMode = ref(false);
  const workspaceWidth = ref(DEFAULT_WORKSPACE_WIDTH);
  const viewportWidth = ref(typeof window === "undefined" ? 1440 : window.innerWidth);
  const viewportHeight = ref(typeof window === "undefined" ? 900 : window.innerHeight);
  const isResizing = ref(false);
  let previousBodyOverflow: string | null = null;
  const canUseTheaterMode = computed(() => viewportWidth.value > 760);

  const theaterMainGridStyle = computed(() => ({
    gridTemplateColumns: `minmax(0, 1fr) 10px ${workspaceWidth.value}px`,
    gridTemplateRows: "minmax(0, 1fr)",
    "--room-visual-viewport-height": `${viewportHeight.value}px`,
    "--room-visual-viewport-offset-top": "0px",
  }));

  function syncViewportSize() {
    if (typeof window === "undefined") return;
    viewportHeight.value = window.innerHeight;
  }

  function handleViewportResize() {
    viewportWidth.value = window.innerWidth;
    workspaceWidth.value = clampWorkspaceWidth(workspaceWidth.value);
    syncViewportSize();
  }

  function loadWorkspaceWidth() {
    if (!roomId.value) {
      workspaceWidth.value = DEFAULT_WORKSPACE_WIDTH;
      return;
    }

    const persisted = readPersistedState<unknown>(
      theaterWorkspaceWidthStorageKey(roomId.value),
      DEFAULT_WORKSPACE_WIDTH,
    );
    workspaceWidth.value =
      typeof persisted === "number"
        ? clampWorkspaceWidth(persisted)
        : DEFAULT_WORKSPACE_WIDTH;
  }

  function saveWorkspaceWidth() {
    if (!roomId.value) return;
    writePersistedState(
      theaterWorkspaceWidthStorageKey(roomId.value),
      workspaceWidth.value,
    );
  }

  function setTheaterMode(value: boolean) {
    if (value === isTheaterMode.value) return;
    if (value && !canUseTheaterMode.value) return;
    isTheaterMode.value = value;
    if (value) {
      loadWorkspaceWidth();
    }
  }

  function stopResize() {
    if (!isResizing.value) return;
    isResizing.value = false;
    saveWorkspaceWidth();
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    window.removeEventListener("pointermove", handlePointerMove);
    window.removeEventListener("pointerup", stopResize);
    window.removeEventListener("pointercancel", stopResize);
  }

  function handlePointerMove(event: PointerEvent) {
    if (!isResizing.value) return;
    const nextWidth = window.innerWidth - event.clientX - THEATER_PADDING;
    workspaceWidth.value = clampWorkspaceWidth(nextWidth);
  }

  function startWorkspaceResize(event: PointerEvent) {
    if (!isTheaterMode.value) return;
    event.preventDefault();
    isResizing.value = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopResize);
    window.addEventListener("pointercancel", stopResize);
  }

  watch(roomId, () => {
    loadWorkspaceWidth();
  });

  onMounted(() => {
    window.addEventListener("resize", handleViewportResize, { passive: true });
  });

  watch(isTheaterMode, (active) => {
    if (typeof document === "undefined") return;

    if (active) {
      previousBodyOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      document.body.classList.add(THEATER_BODY_CLASS);
      return;
    }

    if (previousBodyOverflow != null) {
      document.body.style.overflow = previousBodyOverflow;
      previousBodyOverflow = null;
    }
    document.body.classList.remove(THEATER_BODY_CLASS);
  });

  onBeforeUnmount(() => {
    stopResize();
    window.removeEventListener("resize", handleViewportResize);
    if (previousBodyOverflow != null) {
      document.body.style.overflow = previousBodyOverflow;
    }
    document.body.classList.remove(THEATER_BODY_CLASS);
  });

  return {
    isTheaterMode,
    canUseTheaterMode,
    isResizing,
    theaterMainGridStyle,
    setTheaterMode,
    startWorkspaceResize,
  };
}
