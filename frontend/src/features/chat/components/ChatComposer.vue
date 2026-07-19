<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import {
  CameraIcon,
  FaceSmileIcon,
  PaperAirplaneIcon,
} from "@heroicons/vue/24/outline";
import { useI18n } from "vue-i18n";
import AppIcon from "@/ui/base/AppIcon.vue";
import type { ChatSegment } from "@/features/chat/types";
import { STICKER_DRAG_ACTIVE_ATTR } from "./emoji-picker/stickerDrag.constants";
import type { ChatEmojiPickerSelection } from "./emoji-picker/types";
import ChatEmojiPicker from "./ChatEmojiPicker.vue";
import ChatRichEditor from "./ChatRichEditor.vue";

const props = withDefaults(defineProps<{
  sendLabel?: string;
  sending?: boolean;
  sendMessage?: (segments: ChatSegment[]) => Promise<void> | void;
  captureScreenshot?: () => Promise<void> | void;
  variant?: "default" | "fullscreen";
  showScreenshot?: boolean;
}>(), {
  variant: "default",
  showScreenshot: true,
});

const emit = defineEmits<{
  send: [segments: ChatSegment[]];
  "active-change": [value: boolean];
}>();

const { t } = useI18n();

const rootRef = ref<HTMLElement | null>(null);
const emojiAnchorRef = ref<HTMLElement | null>(null);
const emojiPanelOpen = ref(false);
const canSend = ref(false);
const sendPending = ref(false);
const screenshotPending = ref(false);
const emojiPanelStyle = ref<Record<string, string>>({
  left: "0px",
  top: "0px",
  visibility: "hidden",
});
const emojiTeleportTarget = ref<HTMLElement | "body">("body");
const editorRef = ref<{
  insertQfaceById: (qfaceId: string) => void;
  insertSticker: (sticker: { id: number; url: string; alt?: string }) => void;
  insertText: (text: string) => void;
  collectSegments: () => ChatSegment[];
  clearAndFocus: () => void;
} | null>(null);
let pickerPositionFrame = 0;
const showScreenshotButton = computed(() =>
  props.variant !== "fullscreen" && props.showScreenshot);

function isNarrowViewport() {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(max-width: 640px)").matches;
}

function isComposerFocused() {
  const root = rootRef.value;
  return Boolean(root && root.matches(":focus-within"));
}

function emitActiveState() {
  emit("active-change", emojiPanelOpen.value || isComposerFocused());
}

function updateEmojiPanelPosition() {
  const root = rootRef.value;
  if (!root) return;

  const anchor = props.variant === "fullscreen" && emojiAnchorRef.value
    ? emojiAnchorRef.value
    : root;
  const rect = anchor.getBoundingClientRect();
  const left = rect.left + (rect.width / 2);
  const top = rect.top;
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const horizontalMargin = 8;
  const viewportInset = viewportWidth <= 520 ? 28 : 64;
  const panelWidth = Math.max(0, Math.min(320, viewportWidth - viewportInset));
  const horizontalPadding = (panelWidth / 2) + horizontalMargin;
  const clampedLeft = Math.min(
    Math.max(left, horizontalPadding),
    viewportWidth - horizontalPadding,
  );

  emojiPanelStyle.value = {
    left: `${clampedLeft}px`,
    top: `${top}px`,
    visibility: "visible",
  };
}

function scheduleEmojiPanelPositionUpdate() {
  if (!emojiPanelOpen.value) return;
  if (pickerPositionFrame) {
    cancelAnimationFrame(pickerPositionFrame);
  }

  pickerPositionFrame = window.requestAnimationFrame(() => {
    pickerPositionFrame = 0;
    updateEmojiPanelPosition();
  });
}

function syncEmojiTeleportTarget() {
  emojiTeleportTarget.value = document.fullscreenElement instanceof HTMLElement
    ? document.fullscreenElement
    : "body";
}

function toggleEmojiPanel() {
  emojiPanelOpen.value = !emojiPanelOpen.value;
  emitActiveState();
  if (emojiPanelOpen.value) {
    syncEmojiTeleportTarget();
    emojiPanelStyle.value = {
      left: "0px",
      top: "0px",
      visibility: "hidden",
    };
    void nextTick(() => {
      scheduleEmojiPanelPositionUpdate();
    });
  }
}

function handleCanSendChange(value: boolean) {
  canSend.value = value;
}

async function sendSegmentsDirect(segments: ChatSegment[]) {
  if (segments.length === 0) return;
  if (props.sending || sendPending.value) return;

  sendPending.value = true;
  try {
    if (props.sendMessage) {
      await props.sendMessage(segments);
    } else {
      emit("send", segments);
    }
  } catch {
    // Keep the draft or picker state in place so the user can retry.
  } finally {
    sendPending.value = false;
  }
}

function handleSelectEmoji(selection: ChatEmojiPickerSelection) {
  if (selection.kind === "qface") {
    editorRef.value?.insertQfaceById(selection.emojiId);
  } else if (selection.kind === "sticker") {
    if (props.variant === "fullscreen" || isNarrowViewport()) {
      void sendSegmentsDirect([
        {
          id: `sticker-${selection.stickerId}-${Date.now()}`,
          type: "media",
          alt: selection.alt || `Sticker ${selection.stickerId}`,
          kind: "sticker",
          src: selection.url,
          assetId: String(selection.stickerId),
        },
      ]);
      emojiPanelOpen.value = false;
      emitActiveState();
      return;
    }

    editorRef.value?.insertSticker({
      id: selection.stickerId,
      url: selection.url,
      alt: selection.alt,
    });
  } else {
    editorRef.value?.insertText(selection.value);
  }
  emojiPanelOpen.value = false;
  emitActiveState();
}

function onDocumentPointerDown(event: PointerEvent) {
  const root = rootRef.value;
  const target = event.target as Node | null;
  const panelTarget = target instanceof Element
    ? target.closest("[data-emoji-panel-root='true']")
    : null;
  const stickerDragActive = document.documentElement.hasAttribute(
    STICKER_DRAG_ACTIVE_ATTR,
  );
  if (stickerDragActive) return;
  if (!root || !target || root.contains(target) || panelTarget) return;
  emojiPanelOpen.value = false;
  emitActiveState();
}

function onDocumentKeyDown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  emojiPanelOpen.value = false;
  emitActiveState();
}

async function sendMessage() {
  if (!editorRef.value || !canSend.value) return;
  if (props.sending || sendPending.value) return;

  const segments = editorRef.value.collectSegments();
  if (segments.length === 0) return;

  sendPending.value = true;
  try {
    if (props.sendMessage) {
      await props.sendMessage(segments);
    } else {
      emit("send", segments);
    }

    editorRef.value.clearAndFocus();
    canSend.value = false;
  } catch {
    // Keep the draft in place so the user can retry or edit it.
  } finally {
    sendPending.value = false;
  }
}

async function captureScreenshot() {
  if (!props.captureScreenshot || screenshotPending.value) return;

  screenshotPending.value = true;
  try {
    await props.captureScreenshot();
  } finally {
    screenshotPending.value = false;
  }
}

function handleFocusIn() {
  emitActiveState();
}

function handleFocusOut() {
  void nextTick(() => {
    emitActiveState();
  });
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocumentPointerDown);
  document.addEventListener("keydown", onDocumentKeyDown);
  document.addEventListener("fullscreenchange", syncEmojiTeleportTarget);
  window.addEventListener("resize", scheduleEmojiPanelPositionUpdate);
  window.addEventListener("scroll", scheduleEmojiPanelPositionUpdate, true);
});

onBeforeUnmount(() => {
  emit("active-change", false);
  document.removeEventListener("pointerdown", onDocumentPointerDown);
  document.removeEventListener("keydown", onDocumentKeyDown);
  document.removeEventListener("fullscreenchange", syncEmojiTeleportTarget);
  window.removeEventListener("resize", scheduleEmojiPanelPositionUpdate);
  window.removeEventListener("scroll", scheduleEmojiPanelPositionUpdate, true);
  if (pickerPositionFrame) {
    cancelAnimationFrame(pickerPositionFrame);
  }
});
</script>

<template>
  <div
    ref="rootRef"
    class="composer"
    :class="{ fullscreenComposer: props.variant === 'fullscreen' }"
    @focusin="handleFocusIn"
    @focusout="handleFocusOut"
  >
    <div class="toolbar">
      <div ref="emojiAnchorRef" class="popoverWrap">
        <BaseIconButton
          class="toolButton"
          :aria-label="t('chat.toolbar.emoji')"
          :aria-expanded="emojiPanelOpen"
          @mousedown.prevent
          @click="toggleEmojiPanel"
        >
          <AppIcon :icon="FaceSmileIcon" :size="16" />
        </BaseIconButton>

        <Teleport :to="emojiTeleportTarget">
          <Transition name="floating-fade">
            <ChatEmojiPicker
              v-show="emojiPanelOpen"
              :floating-style="emojiPanelStyle"
              @select-emoji="handleSelectEmoji"
            />
          </Transition>
        </Teleport>
      </div>

      <ChatRichEditor
        v-if="props.variant === 'fullscreen'"
        ref="editorRef"
        variant="compact"
        single-line
        :allow-media="false"
        class="fullscreenEditor"
        @can-send-change="handleCanSendChange"
        @submit-request="sendMessage"
      />

      <BaseIconButton
        v-if="showScreenshotButton"
        class="toolButton"
        :aria-label="t('chat.toolbar.screenshot')"
        :disabled="screenshotPending"
        @click="captureScreenshot"
      >
        <AppIcon :icon="CameraIcon" :size="16" />
      </BaseIconButton>

      <BaseIconButton
        class="sendButton"
        :aria-label="props.sendLabel || 'Send'"
        :disabled="!canSend || props.sending || sendPending"
        @click="sendMessage"
      >
        <AppIcon :icon="PaperAirplaneIcon" :size="16" />
      </BaseIconButton>
    </div>

    <ChatRichEditor
      v-if="props.variant !== 'fullscreen'"
      ref="editorRef"
      @can-send-change="handleCanSendChange"
      @submit-request="sendMessage"
    />
  </div>
</template>

<style scoped>
.composer {
  display: grid;
  gap: 6px;
  position: relative;
}

.composer.fullscreenComposer {
  min-width: 0;
  width: 100%;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  margin-top: -2px;
}

.fullscreenComposer .toolbar {
  gap: 8px;
  margin-top: 0;
}

.fullscreenEditor {
  min-width: 0;
  flex: 1 1 auto;
}

.toolButton {
  width: 28px;
  height: 28px;
  min-width: 28px;
  opacity: 0.82;
  border-radius: 10px;
}

.fullscreenComposer .toolButton {
  width: 34px;
  height: 34px;
  min-width: 34px;
  color: rgb(238 244 252 / 0.94);
  background: rgb(11 16 23 / 0.72);
  border: 1px solid rgb(255 255 255 / 0.14);
}

.fullscreenComposer .toolButton:hover:not(:disabled) {
  background: rgb(22 31 44 / 0.86);
}

.disabledTool {
  opacity: 0.42;
}

.popoverWrap {
  position: static;
  display: inline-flex;
}

.sendButton {
  width: 34px;
  height: 34px;
  min-width: 34px;
  margin-left: auto;
  background: color-mix(in srgb, var(--c-primary) 8%, var(--c-surface));
  color: var(--c-primary);
  border-radius: 12px;
}

.fullscreenComposer .sendButton {
  width: 38px;
  height: 38px;
  min-width: 38px;
  margin-left: 0;
  color: rgb(238 244 252 / 0.96);
  background: color-mix(in srgb, var(--c-primary) 36%, rgb(11 16 23));
  border: 1px solid color-mix(in srgb, var(--c-primary) 44%, rgb(255 255 255 / 0.16));
}

.fullscreenComposer .sendButton:hover:not(:disabled) {
  background: color-mix(in srgb, var(--c-primary) 46%, rgb(22 31 44));
}

.sendButton:hover {
  background: color-mix(in srgb, var(--c-primary) 12%, var(--c-surface));
}

.sendButton:disabled {
  opacity: 0.45;
}

.floating-fade-enter-active,
.floating-fade-leave-active {
  transition: opacity 100ms ease, transform 120ms ease;
}

.floating-fade-enter-from,
.floating-fade-leave-to {
  opacity: 0;
  transform: translate(-50%, calc(-100% - 4px));
}

.floating-fade-enter-to,
.floating-fade-leave-from {
  opacity: 1;
  transform: translate(-50%, calc(-100% - 12px));
}

:global(body.icinema-room-theater-active [data-emoji-panel-root="true"]) {
  z-index: 180;
}

:global(body.icinema-room-web-fullscreen-active [data-emoji-panel-root="true"]) {
  z-index: 180;
}
</style>
