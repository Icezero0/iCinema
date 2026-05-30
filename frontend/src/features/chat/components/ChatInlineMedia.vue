<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, toRef, watch } from "vue";
import {
  ArrowDownTrayIcon,
  ClipboardDocumentIcon,
  EyeIcon,
  HeartIcon,
} from "@heroicons/vue/24/outline";
import { useI18n } from "vue-i18n";
import { useChatMediaActions } from "@/features/chat/composables/useChatMediaActions";
import { useChatMediaSelection } from "@/features/chat/composables/useChatMediaSelection";
import BaseMenuItem from "@/ui/base/BaseMenuItem.vue";

const props = withDefaults(defineProps<{
  kind: "emoji" | "image" | "sticker";
  src?: string;
  alt: string;
  assetId?: string | null;
  emojiId?: string;
  animated?: boolean;
  context?: "editor" | "message";
  displayMode?: "inline" | "block";
  selectedRange?: boolean;
  selectedNode?: boolean;
}>(), {
  context: "message",
  displayMode: "inline",
  src: undefined,
  assetId: undefined,
  emojiId: undefined,
  animated: false,
  selectedRange: false,
  selectedNode: false,
});

const { t } = useI18n();
const rootRef = ref<HTMLElement | null>(null);
const imageRef = ref<HTMLImageElement | null>(null);
const contextMenuRef = ref<HTMLElement | null>(null);
const mediaNaturalWidth = ref(0);
const mediaNaturalHeight = ref(0);
const mediaAvailableWidth = ref<number | null>(null);
const measuredBlockWidth = ref<number | null>(null);
const contextMenuOpen = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);
const contextMenuTeleportTarget = ref<HTMLElement | "body">("body");
let imageResizeObserver: ResizeObserver | null = null;
let contentResizeObserver: ResizeObserver | null = null;

const {
  mergedSelectedRange,
  mergedSelectedNode,
  selectMessageNode,
} = useChatMediaSelection({
  rootRef,
  context: toRef(props, "context"),
  kind: toRef(props, "kind"),
  src: toRef(props, "src"),
  alt: toRef(props, "alt"),
  assetId: toRef(props, "assetId"),
  emojiId: toRef(props, "emojiId"),
  animated: toRef(props, "animated"),
  selectedRange: toRef(props, "selectedRange"),
  selectedNode: toRef(props, "selectedNode"),
});

const shouldMeasureBlockWidth = computed(() => (
  props.context === "message" &&
  props.displayMode === "block" &&
  props.kind === "sticker"
));

const rootInlineStyle = computed(() => {
  if (shouldMeasureBlockWidth.value && measuredBlockWidth.value) {
    return {
      width: `${measuredBlockWidth.value}px`,
    };
  }

  return undefined;
});

const isMessageMedia = computed(() => (
  props.context === "message" &&
  !!props.src &&
  (props.kind === "image" || props.kind === "sticker")
));

const messageMediaImageStyle = computed(() => {
  if (
    props.context !== "message" ||
    (props.kind !== "image" && props.kind !== "sticker")
  ) {
    return undefined;
  }

  const image = imageRef.value;
  const naturalWidth = mediaNaturalWidth.value || image?.naturalWidth || 0;
  const naturalHeight = mediaNaturalHeight.value || image?.naturalHeight || 0;

  if (!naturalWidth || !naturalHeight) {
    return props.displayMode === "block"
      ? props.kind === "sticker"
        ? {
            width: "112px",
            height: "112px",
          }
        : {
            width: "min(280px, 100%)",
            aspectRatio: "16 / 9",
          }
      : undefined;
  }

  const aspectRatio = naturalWidth / naturalHeight;
  const longSide = Math.max(naturalWidth, naturalHeight);
  const availableWidth = mediaAvailableWidth.value;

  if (longSide <= 128) {
    const smallImageScale =
      availableWidth && availableWidth > 0
        ? Math.min(1, availableWidth / naturalWidth)
        : 1;

    return {
      width: `${Math.round(naturalWidth * smallImageScale)}px`,
      height: `${Math.round(naturalHeight * smallImageScale)}px`,
    };
  }

  let targetLongSide = 112;
  if (aspectRatio > 1.45) {
    targetLongSide = 280;
  } else if (aspectRatio < 0.7) {
    targetLongSide = 128;
  }

  const preferredScale = targetLongSide / longSide;
  const constrainedScale =
    availableWidth && availableWidth > 0
      ? Math.min(preferredScale, availableWidth / naturalWidth)
      : preferredScale;

  const scale = constrainedScale;
  const width = naturalWidth * scale;
  const height = naturalHeight * scale;

  return {
    width: `${Math.round(width)}px`,
    height: `${Math.round(height)}px`,
  };
});

function closeContextMenu() {
  contextMenuOpen.value = false;
}

function syncContextMenuTeleportTarget() {
  contextMenuTeleportTarget.value = document.fullscreenElement instanceof HTMLElement
    ? document.fullscreenElement
    : "body";
}

const {
  openMediaViewer,
  copyMedia,
  saveMedia,
  collectMedia,
  viewMedia,
} = useChatMediaActions({
  kind: toRef(props, "kind"),
  src: toRef(props, "src"),
  alt: toRef(props, "alt"),
  assetId: toRef(props, "assetId"),
  closeContextMenu,
  selectMessageNode,
});

function positionContextMenu() {
  const menu = contextMenuRef.value;
  if (!menu) return;

  const viewportPadding = 8;
  const rect = menu.getBoundingClientRect();
  contextMenuX.value = Math.min(
    contextMenuX.value,
    window.innerWidth - rect.width - viewportPadding,
  );
  contextMenuY.value = Math.min(
    contextMenuY.value,
    window.innerHeight - rect.height - viewportPadding,
  );
  contextMenuX.value = Math.max(viewportPadding, contextMenuX.value);
  contextMenuY.value = Math.max(viewportPadding, contextMenuY.value);
}

async function openContextMenuAt(x: number, y: number) {
  syncContextMenuTeleportTarget();
  contextMenuX.value = x;
  contextMenuY.value = y;
  contextMenuOpen.value = true;
  await nextTick();
  positionContextMenu();
}

function syncMeasuredBlockWidth() {
  if (!shouldMeasureBlockWidth.value) {
    measuredBlockWidth.value = null;
    return;
  }

  const image = imageRef.value;
  if (!image) return;
  if (!image.complete || image.naturalWidth <= 0 || image.naturalHeight <= 0) return;

  const nextWidth = Math.round(image.getBoundingClientRect().width);
  measuredBlockWidth.value = nextWidth > 24 ? nextWidth : null;
}

function syncMediaAvailableWidth() {
  const root = rootRef.value;
  const content = root?.closest(".content");
  const contentWidth =
    content instanceof HTMLElement
      ? Math.round(content.getBoundingClientRect().width)
      : null;
  const bubble = root?.closest(".bubble");
  const bubbleStyle =
    bubble instanceof HTMLElement &&
    !bubble.classList.contains("bubbleless")
      ? window.getComputedStyle(bubble)
      : null;
  const bubbleInlineChrome = bubbleStyle
    ? Number.parseFloat(bubbleStyle.paddingLeft) +
      Number.parseFloat(bubbleStyle.paddingRight) +
      Number.parseFloat(bubbleStyle.borderLeftWidth) +
      Number.parseFloat(bubbleStyle.borderRightWidth)
    : 0;
  const nextWidth = contentWidth == null
    ? null
    : Math.max(0, Math.round(contentWidth - bubbleInlineChrome));

  mediaAvailableWidth.value =
    nextWidth && nextWidth > 24 ? nextWidth : null;
}

function syncMediaNaturalSize() {
  const image = imageRef.value;
  mediaNaturalWidth.value = image?.naturalWidth ?? 0;
  mediaNaturalHeight.value = image?.naturalHeight ?? 0;
}

function handleImageLoad() {
  syncMediaNaturalSize();
  syncMediaAvailableWidth();
  syncMeasuredBlockWidth();
}

function handleContextMenu(event: MouseEvent) {
  if (!isMessageMedia.value) return;

  event.preventDefault();
  event.stopPropagation();
  selectMessageNode();
  void openContextMenuAt(event.clientX, event.clientY);
}

onMounted(() => {
  if (props.context !== "message") return;

  syncContextMenuTeleportTarget();
  document.addEventListener("fullscreenchange", syncContextMenuTeleportTarget);
  syncMediaNaturalSize();
  syncMediaAvailableWidth();

  if (shouldMeasureBlockWidth.value && typeof ResizeObserver !== "undefined" && imageRef.value) {
    imageResizeObserver = new ResizeObserver(() => {
      syncMeasuredBlockWidth();
    });
    imageResizeObserver.observe(imageRef.value);
  }

  if (typeof ResizeObserver !== "undefined") {
    const content = rootRef.value?.closest(".content");
    if (content instanceof HTMLElement) {
      contentResizeObserver = new ResizeObserver(() => {
        syncMediaAvailableWidth();
      });
      contentResizeObserver.observe(content);
    }
  }
});

onBeforeUnmount(() => {
  if (props.context !== "message") return;
  document.removeEventListener("fullscreenchange", syncContextMenuTeleportTarget);
  imageResizeObserver?.disconnect();
  imageResizeObserver = null;
  contentResizeObserver?.disconnect();
  contentResizeObserver = null;
});

watch(
  () => props.src,
  () => {
    mediaNaturalWidth.value = 0;
    mediaNaturalHeight.value = 0;
    mediaAvailableWidth.value = null;
    measuredBlockWidth.value = null;
  },
);

watch(contextMenuOpen, (isOpen) => {
  if (!isOpen) return;

  const onPointerDown = (event: PointerEvent) => {
    const target = event.target as Node | null;
    const menu = contextMenuRef.value;
    const root = rootRef.value;

    if (
      (menu && target && menu.contains(target)) ||
      (root && target && root.contains(target))
    ) {
      return;
    }

    closeContextMenu();
  };

  const onKeydown = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      closeContextMenu();
    }
  };

  const onWindowChange = () => {
    closeContextMenu();
  };

  document.addEventListener("pointerdown", onPointerDown, true);
  document.addEventListener("keydown", onKeydown);
  window.addEventListener("resize", onWindowChange);
  window.addEventListener("scroll", onWindowChange, true);

  const stop = watch(contextMenuOpen, (nextOpen) => {
    if (nextOpen) return;
    document.removeEventListener("pointerdown", onPointerDown, true);
    document.removeEventListener("keydown", onKeydown);
    window.removeEventListener("resize", onWindowChange);
    window.removeEventListener("scroll", onWindowChange, true);
    stop();
  });
});
</script>

<template>
  <span
    ref="rootRef"
    class="chatInlineMedia"
    :style="rootInlineStyle"
    :class="[
      `chatInlineMedia--${props.kind}`,
      `chatInlineMedia--${props.context}`,
      `chatInlineMedia--${props.displayMode}`,
      {
        'chatInlineMedia--selected-range': mergedSelectedRange,
        'chatInlineMedia--selected-node': mergedSelectedNode,
      },
    ]"
    draggable="false"
    @click="selectMessageNode"
    @dblclick.stop="openMediaViewer"
    @contextmenu="handleContextMenu"
  >
    <img
      v-if="props.src"
      ref="imageRef"
      class="chatInlineMedia__image"
      :class="[
        `chatInlineMedia__image--${props.kind}`,
        `chatInlineMedia__image--${props.context}`,
      ]"
      :src="props.src"
      :alt="props.alt"
      :data-kind="props.kind"
      :data-asset-id="props.assetId || null"
      :data-emoji-id="props.emojiId || null"
      :data-animated="props.animated ? 'true' : null"
      :style="messageMediaImageStyle"
      draggable="false"
      @load="handleImageLoad"
    >
    <span
      v-else
      class="chatInlineMedia__placeholder"
      :class="`chatInlineMedia__placeholder--${props.context}`"
    >
      <span class="chatInlineMedia__label">{{ props.alt }}</span>
    </span>
  </span>

  <Teleport :to="contextMenuTeleportTarget">
    <Transition name="contextMenuFade">
      <div
        v-if="contextMenuOpen"
        ref="contextMenuRef"
        class="contextMenu"
        :style="{
          left: `${contextMenuX}px`,
          top: `${contextMenuY}px`,
        }"
        role="menu"
      >
        <BaseMenuItem :icon="EyeIcon" @click="viewMedia">
          {{ t("chat.mediaMenu.view") }}
        </BaseMenuItem>
        <BaseMenuItem :icon="ClipboardDocumentIcon" @click="copyMedia">
          {{ t("chat.mediaMenu.copy") }}
        </BaseMenuItem>
        <BaseMenuItem :icon="HeartIcon" @click="collectMedia">
          {{ t("chat.mediaMenu.collect") }}
        </BaseMenuItem>
        <BaseMenuItem :icon="ArrowDownTrayIcon" @click="saveMedia">
          {{ t("chat.mediaMenu.save") }}
        </BaseMenuItem>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.chatInlineMedia {
  position: relative;
  display: inline-flex;
  vertical-align: text-bottom;
  border-radius: 0;
}

.chatInlineMedia::selection,
.chatInlineMedia *::selection {
  background: transparent;
}

.chatInlineMedia--message.chatInlineMedia--block.chatInlineMedia--image,
.chatInlineMedia--message.chatInlineMedia--block.chatInlineMedia--sticker {
  display: inline-block;
  width: auto;
  max-width: 100%;
  line-height: 0;
}

.chatInlineMedia--message.chatInlineMedia--image,
.chatInlineMedia--message.chatInlineMedia--sticker {
  cursor: pointer;
}

.chatInlineMedia--selected-range::after {
  content: "";
  position: absolute;
  inset: -0.05em;
  border-radius: 0;
  background: rgb(59 130 246 / 0.28);
  pointer-events: none;
}

.chatInlineMedia--selected-node::after {
  content: "";
  position: absolute;
  inset: -4px;
  border-radius: 16px;
  border: 2px solid rgb(59 130 246 / 0.7);
  box-shadow:
    0 0 0 1px rgb(255 255 255 / 0.8),
    0 8px 18px rgb(59 130 246 / 0.16);
  pointer-events: none;
}

.chatInlineMedia__image {
  display: block;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 18%, var(--c-border));
  object-fit: cover;
  -webkit-user-drag: none;
}

.chatInlineMedia__image--editor.chatInlineMedia__image--image {
  width: auto;
  height: auto;
  max-width: 92px;
  max-height: 92px;
  object-fit: contain;
}

.chatInlineMedia__image--editor.chatInlineMedia__image--sticker {
  width: auto;
  height: auto;
  max-width: 110px;
  max-height: 110px;
  object-fit: contain;
  background: color-mix(in srgb, var(--c-surface) 88%, white);
}

.chatInlineMedia__image--editor.chatInlineMedia__image--emoji,
.chatInlineMedia__image--message.chatInlineMedia__image--emoji {
  width: 1.35em;
  height: 1.35em;
  border: 0;
  border-radius: 0;
  margin: 0 0.12em 0 0.08em;
  background: transparent;
  object-fit: contain;
  vertical-align: -0.24em;
}

.chatInlineMedia__image--message.chatInlineMedia__image--image {
  width: auto;
  height: auto;
  max-width: min(280px, 100%);
  max-height: 180px;
  object-fit: contain;
}

.chatInlineMedia__image--message.chatInlineMedia__image--sticker {
  width: auto;
  height: auto;
  max-width: 128px;
  max-height: 128px;
  object-fit: contain;
  border: 0;
  border-radius: 12px;
  background: transparent;
}

.chatInlineMedia__placeholder {
  display: grid;
  place-items: center;
  border-radius: 12px;
  border: 1px dashed color-mix(in srgb, var(--c-primary) 22%, var(--c-border));
  background:
    linear-gradient(
      160deg,
      color-mix(in srgb, var(--c-surface) 82%, white),
      color-mix(in srgb, var(--c-surface) 72%, var(--c-bg))
    );
}

.chatInlineMedia__placeholder--message {
  width: min(100%, 280px);
  aspect-ratio: 1;
}

.chatInlineMedia__label {
  font-size: 12px;
  color: var(--c-text-muted);
}

.contextMenu {
  position: fixed;
  min-width: 148px;
  padding: 6px;
  border: 1px solid var(--c-border);
  border-radius: 14px;
  background: color-mix(in srgb, var(--c-surface) 94%, var(--c-bg));
  box-shadow: 0 18px 50px rgb(0 0 0 / 0.14);
  z-index: 240;
}

.contextMenuFade-enter-active,
.contextMenuFade-leave-active {
  transition: opacity 120ms ease, transform 120ms ease;
}

.contextMenuFade-enter-from,
.contextMenuFade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
