import {
  computed,
  onBeforeUnmount,
  ref,
  type ComponentPublicInstance,
  type CSSProperties,
} from "vue";
import type { StickerWithDisplayUrl } from "@/stores/stickers.store";
import { STICKER_DRAG_ACTIVE_ATTR } from "./stickerDrag.constants";

type ReadableRef<T> = {
  readonly value: T;
};

type StickerPointerDragState = {
  stickerId: number;
  pointerId: number;
  startX: number;
  startY: number;
  offsetX: number;
  offsetY: number;
  width: number;
  height: number;
  left: number;
  top: number;
  targetStickerId: number | null;
  lastOrderKey: string;
  moved: boolean;
};

type StickerPointerDragOptions = {
  stickerLibrary: ReadableRef<StickerWithDisplayUrl[]>;
  isEditing: ReadableRef<boolean | undefined>;
  closePreview: () => void;
  reorder: (stickerIds: number[]) => void;
};

export function useStickerPointerDrag(options: StickerPointerDragOptions) {
  const dragOverlayRef = ref<HTMLElement | null>(null);
  const draggingStickerId = ref<number | null>(null);
  const pointerDragState = ref<StickerPointerDragState | null>(null);
  let dragSourceElement: HTMLElement | null = null;

  const draggedSticker = computed(() => (
    pointerDragState.value == null
      ? null
      : options.stickerLibrary.value.find(
        (sticker) => sticker.id === pointerDragState.value?.stickerId,
      ) ?? null
  ));
  const dragOverlayStyle = computed<CSSProperties | undefined>(() => {
    const state = pointerDragState.value;
    if (!state) return undefined;

    return {
      left: `${state.left}px`,
      top: `${state.top}px`,
      width: `${state.width}px`,
      height: `${state.height}px`,
    };
  });

  function setDragOverlayRef(element: Element | ComponentPublicInstance | null) {
    dragOverlayRef.value = element instanceof HTMLElement ? element : null;
  }

  function removeWindowDragListeners() {
    if (typeof window === "undefined") return;

    window.removeEventListener("pointermove", handleWindowPointerMove);
    window.removeEventListener("pointerup", handleWindowPointerUp);
    window.removeEventListener("pointercancel", handleWindowPointerCancel);
  }

  function resetPointerDrag() {
    removeWindowDragListeners();
    if (typeof document !== "undefined") {
      document.documentElement.removeAttribute(STICKER_DRAG_ACTIVE_ATTR);
    }
    pointerDragState.value = null;
    draggingStickerId.value = null;
    dragSourceElement = null;
  }

  function addWindowDragListeners() {
    if (typeof window === "undefined") return;

    window.addEventListener("pointermove", handleWindowPointerMove, { passive: false });
    window.addEventListener("pointerup", handleWindowPointerUp, { passive: false });
    window.addEventListener("pointercancel", handleWindowPointerCancel, { passive: false });
  }

  function moveDragOverlay(clientX: number, clientY: number) {
    const state = pointerDragState.value;
    const overlay = dragOverlayRef.value;
    if (!state) return;

    state.left = clientX - state.offsetX;
    state.top = clientY - state.offsetY;

    if (!overlay) return;

    overlay.style.left = `${state.left}px`;
    overlay.style.top = `${state.top}px`;
  }

  function getStickerOptionFromPoint(clientX: number, clientY: number) {
    const state = pointerDragState.value;
    if (!state || typeof document === "undefined") return null;

    const elements = document.elementsFromPoint(clientX, clientY);
    for (const element of elements) {
      const option = element.closest<HTMLElement>("[data-sticker-id]");
      const stickerId = Number(option?.dataset.stickerId);

      if (
        option &&
        Number.isFinite(stickerId) &&
        stickerId > 0 &&
        stickerId !== state.stickerId
      ) {
        return {
          option,
          stickerId,
        };
      }
    }

    return null;
  }

  function syncDraftOrderFromPointer(clientX: number, clientY: number) {
    const state = pointerDragState.value;
    const target = getStickerOptionFromPoint(clientX, clientY);
    if (!state || !target) {
      if (state) {
        state.targetStickerId = null;
      }
      return;
    }

    const ids = options.stickerLibrary.value.map((sticker) => sticker.id);
    const fromIndex = ids.indexOf(state.stickerId);
    const targetIndex = ids.indexOf(target.stickerId);
    if (fromIndex < 0 || targetIndex < 0) return;

    const nextIds = [...ids];
    nextIds.splice(fromIndex, 1);
    nextIds.splice(targetIndex, 0, state.stickerId);

    const nextOrderKey = nextIds.join(",");
    state.targetStickerId = target.stickerId;
    if (nextOrderKey === state.lastOrderKey) return;

    state.lastOrderKey = nextOrderKey;
    options.reorder(nextIds);
  }

  function handleStickerPointerDown(stickerId: number, event: PointerEvent) {
    if (!options.isEditing.value) {
      event.preventDefault();
      return;
    }

    if (event.pointerType === "mouse" && event.button !== 0) return;

    const target = event.target as HTMLElement | null;
    if (target?.closest(".stickerRemoveButton")) return;
    const option = event.currentTarget as HTMLElement | null;
    const rect = option?.getBoundingClientRect();
    if (!rect) return;

    options.closePreview();
    event.preventDefault();
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute(STICKER_DRAG_ACTIVE_ATTR, "true");
    }
    draggingStickerId.value = stickerId;
    dragSourceElement = option;
    pointerDragState.value = {
      stickerId,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
      width: rect.width,
      height: rect.height,
      left: rect.left,
      top: rect.top,
      targetStickerId: null,
      lastOrderKey: options.stickerLibrary.value.map((sticker) => sticker.id).join(","),
      moved: false,
    };

    dragSourceElement?.setPointerCapture?.(event.pointerId);
    addWindowDragListeners();
  }

  function handleWindowPointerMove(event: PointerEvent) {
    const state = pointerDragState.value;
    if (!options.isEditing.value || !state || state.pointerId !== event.pointerId) return;

    event.preventDefault();

    const deltaX = event.clientX - state.startX;
    const deltaY = event.clientY - state.startY;
    state.moved = state.moved || Math.hypot(deltaX, deltaY) > 3;
    moveDragOverlay(event.clientX, event.clientY);

    if (state.moved) {
      syncDraftOrderFromPointer(event.clientX, event.clientY);
    }
  }

  function handleWindowPointerUp(event: PointerEvent) {
    const state = pointerDragState.value;
    if (!options.isEditing.value || !state || state.pointerId !== event.pointerId) return;

    event.preventDefault();
    dragSourceElement?.releasePointerCapture?.(event.pointerId);
    resetPointerDrag();
  }

  function handleWindowPointerCancel(event: PointerEvent) {
    const state = pointerDragState.value;
    if (!state || state.pointerId !== event.pointerId) return;

    dragSourceElement?.releasePointerCapture?.(event.pointerId);
    resetPointerDrag();
  }

  onBeforeUnmount(resetPointerDrag);

  return {
    draggedSticker,
    draggingStickerId,
    dragOverlayStyle,
    setDragOverlayRef,
    pointerDragState,
    handleStickerPointerDown,
  };
}
