<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import {
  CameraIcon,
  FaceSmileIcon,
  PaperAirplaneIcon,
} from "@heroicons/vue/24/outline";
import { useI18n } from "vue-i18n";
import AppIcon from "@/ui/base/AppIcon.vue";
import type { ChatSegment } from "@/features/chat/types";
import ChatEmojiPicker from "./ChatEmojiPicker.vue";
import ChatRichEditor from "./ChatRichEditor.vue";

const props = defineProps<{
  sendLabel?: string;
}>();

const emit = defineEmits<{
  send: [segments: ChatSegment[]];
}>();

type PickerSelection =
  | { kind: "qface"; emojiId: string }
  | { kind: "unicode_emoji"; value: string };

const { t } = useI18n();

const rootRef = ref<HTMLElement | null>(null);
const emojiPanelOpen = ref(false);
const canSend = ref(false);
const emojiPanelStyle = ref<Record<string, string>>({
  left: "0px",
  top: "0px",
  visibility: "hidden",
});
const editorRef = ref<{
  insertEmojiById: (emojiId: string) => void;
  insertText: (text: string) => void;
  collectSegments: () => ChatSegment[];
  clearAndFocus: () => void;
} | null>(null);
let pickerPositionFrame = 0;

function updateEmojiPanelPosition() {
  const root = rootRef.value;
  if (!root) return;

  const rect = root.getBoundingClientRect();
  const left = rect.left + (rect.width / 2);
  const top = rect.top;
  const horizontalPadding = 32;
  const clampedLeft = Math.min(
    Math.max(left, horizontalPadding),
    window.innerWidth - horizontalPadding,
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

function toggleEmojiPanel() {
  emojiPanelOpen.value = !emojiPanelOpen.value;
  if (emojiPanelOpen.value) {
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

function handleSelectEmoji(selection: PickerSelection) {
  if (selection.kind === "qface") {
    editorRef.value?.insertEmojiById(selection.emojiId);
  } else {
    editorRef.value?.insertText(selection.value);
  }
  emojiPanelOpen.value = false;
}

function onDocumentPointerDown(event: PointerEvent) {
  const root = rootRef.value;
  const target = event.target as Node | null;
  const panelTarget = target instanceof Element
    ? target.closest("[data-emoji-panel-root='true']")
    : null;
  if (!root || !target || root.contains(target) || panelTarget) return;
  emojiPanelOpen.value = false;
}

function onDocumentKeyDown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  emojiPanelOpen.value = false;
}

function sendMockMessage() {
  if (!editorRef.value || !canSend.value) return;

  const segments = editorRef.value.collectSegments();
  if (segments.length === 0) return;

  emit("send", segments);
  editorRef.value.clearAndFocus();
  canSend.value = false;
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocumentPointerDown);
  document.addEventListener("keydown", onDocumentKeyDown);
  window.addEventListener("resize", scheduleEmojiPanelPositionUpdate);
  window.addEventListener("scroll", scheduleEmojiPanelPositionUpdate, true);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onDocumentPointerDown);
  document.removeEventListener("keydown", onDocumentKeyDown);
  window.removeEventListener("resize", scheduleEmojiPanelPositionUpdate);
  window.removeEventListener("scroll", scheduleEmojiPanelPositionUpdate, true);
  if (pickerPositionFrame) {
    cancelAnimationFrame(pickerPositionFrame);
  }
});
</script>

<template>
  <div ref="rootRef" class="composer">
    <div class="toolbar">
      <div class="popoverWrap">
        <BaseIconButton
          class="toolButton"
          :aria-label="t('chat.toolbar.emoji')"
          :aria-expanded="emojiPanelOpen"
          @mousedown.prevent
          @click="toggleEmojiPanel"
        >
          <AppIcon :icon="FaceSmileIcon" :size="16" />
        </BaseIconButton>

        <Teleport to="body">
          <Transition name="floating-fade">
            <ChatEmojiPicker
              v-show="emojiPanelOpen"
              :floating-style="emojiPanelStyle"
              @select-emoji="handleSelectEmoji"
            />
          </Transition>
        </Teleport>
      </div>

      <BaseIconButton
        class="toolButton disabledTool"
        :aria-label="t('chat.toolbar.screenshot')"
        disabled
      >
        <AppIcon :icon="CameraIcon" :size="16" />
      </BaseIconButton>

      <BaseIconButton
        class="sendButton"
        :aria-label="props.sendLabel || 'Send'"
        :disabled="!canSend"
        @click="sendMockMessage"
      >
        <AppIcon :icon="PaperAirplaneIcon" :size="16" />
      </BaseIconButton>
    </div>

    <ChatRichEditor
      ref="editorRef"
      @can-send-change="handleCanSendChange"
    />
  </div>
</template>

<style scoped>
.composer {
  display: grid;
  gap: 6px;
  position: relative;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  margin-top: -2px;
}

.toolButton {
  width: 28px;
  height: 28px;
  min-width: 28px;
  opacity: 0.82;
  border-radius: 10px;
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
</style>
