<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import {
  CameraIcon,
  FaceSmileIcon,
  PaperAirplaneIcon,
} from "@heroicons/vue/24/outline";
import { useI18n } from "vue-i18n";
import AppIcon from "@/ui/base/AppIcon.vue";
import type { ChatSection } from "@/features/chat/types";
import ChatEmojiPicker from "./ChatEmojiPicker.vue";
import ChatRichEditor from "./ChatRichEditor.vue";

const props = defineProps<{
  sendLabel?: string;
}>();

const emit = defineEmits<{
  send: [sections: ChatSection[]];
}>();

const { t } = useI18n();

const rootRef = ref<HTMLElement | null>(null);
const emojiPanelOpen = ref(false);
const canSend = ref(false);
const editorRef = ref<{
  insertEmojiById: (emojiId: string) => void;
  collectSections: () => ChatSection[];
  clearAndFocus: () => void;
} | null>(null);

function toggleEmojiPanel() {
  emojiPanelOpen.value = !emojiPanelOpen.value;
}

function handleCanSendChange(value: boolean) {
  canSend.value = value;
}

function handleSelectEmoji(emojiId: string) {
  editorRef.value?.insertEmojiById(emojiId);
  emojiPanelOpen.value = false;
}

function onDocumentPointerDown(event: PointerEvent) {
  const root = rootRef.value;
  const target = event.target as Node | null;
  if (!root || !target || root.contains(target)) return;
  emojiPanelOpen.value = false;
}

function onDocumentKeyDown(event: KeyboardEvent) {
  if (event.key !== "Escape") return;
  emojiPanelOpen.value = false;
}

function sendMockMessage() {
  if (!editorRef.value || !canSend.value) return;

  const sections = editorRef.value.collectSections();
  if (sections.length === 0) return;

  emit("send", sections);
  editorRef.value.clearAndFocus();
  canSend.value = false;
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocumentPointerDown);
  document.addEventListener("keydown", onDocumentKeyDown);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onDocumentPointerDown);
  document.removeEventListener("keydown", onDocumentKeyDown);
});
</script>

<template>
  <div ref="rootRef" class="composer">
    <div class="toolbar">
      <div class="popoverWrap emojiWrap">
        <BaseIconButton
          class="toolButton"
          :aria-label="t('chat.toolbar.emoji')"
          :aria-expanded="emojiPanelOpen"
          @click="toggleEmojiPanel"
        >
          <AppIcon :icon="FaceSmileIcon" :size="16" />
        </BaseIconButton>

        <Transition name="floating-fade">
          <ChatEmojiPicker
            v-if="emojiPanelOpen"
            @select-emoji="handleSelectEmoji"
          />
        </Transition>
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
  position: relative;
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

:deep(.emojiPanel) {
  position: absolute;
  left: 0;
  bottom: calc(100% + 12px);
  width: min(320px, calc(100vw - 64px));
  border: 1px solid var(--c-border);
  border-radius: 16px;
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--c-surface) 94%, white),
      color-mix(in srgb, var(--c-surface) 90%, var(--c-bg))
    );
  box-shadow: 0 18px 40px rgb(0 0 0 / 0.12);
  padding: 12px;
  z-index: 8;
}

:deep(.emojiTabs) {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

:deep(.emojiTab) {
  height: 32px;
  border: 1px solid var(--c-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--c-surface) 92%, white);
  color: var(--c-text-muted);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition:
    background-color 160ms ease,
    color 160ms ease,
    border-color 160ms ease,
    transform 160ms ease;
}

:deep(.emojiTab:hover) {
  transform: translateY(-1px);
  color: var(--c-text);
}

:deep(.emojiTab.active) {
  color: var(--c-primary);
  border-color: color-mix(in srgb, var(--c-primary) 24%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 10%, var(--c-surface));
}

:deep(.emojiPanelBody) {
  margin-top: 10px;
  max-height: 244px;
  min-height: 172px;
  overflow: auto;
  padding-right: 4px;
}

:deep(.emojiPanelBody::-webkit-scrollbar) {
  width: 8px;
}

:deep(.emojiPanelBody::-webkit-scrollbar-thumb) {
  background: color-mix(in srgb, var(--c-text-muted) 34%, transparent);
  border-radius: 999px;
}

:deep(.emojiGrid) {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

:deep(.emojiOption) {
  min-height: 62px;
  padding: 8px 6px;
  border: 1px solid color-mix(in srgb, var(--c-border) 88%, white);
  border-radius: 12px;
  background: color-mix(in srgb, var(--c-surface) 88%, white);
  display: grid;
  gap: 6px;
  justify-items: center;
  align-content: start;
  cursor: pointer;
  transition:
    transform 160ms ease,
    background-color 160ms ease,
    border-color 160ms ease,
    box-shadow 180ms ease;
}

:deep(.emojiOption:hover) {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--c-primary) 20%, var(--c-border));
  background: color-mix(in srgb, var(--c-primary) 6%, var(--c-surface));
  box-shadow: 0 8px 16px rgb(0 0 0 / 0.05);
}

:deep(.emojiOptionImage) {
  width: 26px;
  height: 26px;
  object-fit: contain;
}

:deep(.emojiOptionLabel) {
  font-size: 11px;
  line-height: 1.2;
  color: var(--c-text-muted);
  text-align: center;
  word-break: break-word;
}

:deep(.emojiEmpty) {
  min-height: 172px;
  display: grid;
  place-items: center;
  border: 1px dashed color-mix(in srgb, var(--c-border) 88%, white);
  border-radius: 14px;
  color: var(--c-text-muted);
  font-size: 12px;
  text-align: center;
  padding: 18px;
}

.floating-fade-enter-active,
.floating-fade-leave-active {
  transition: opacity 140ms ease, transform 160ms ease;
}

.floating-fade-enter-from,
.floating-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.floating-fade-enter-to,
.floating-fade-leave-from {
  opacity: 1;
  transform: translateY(0);
}
</style>
