<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { EditorContent, useEditor } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";
import InlineMedia from "@/features/chat/editor/InlineMedia";
import InlineEmoji from "@/features/chat/editor/InlineEmoji";
import TrailingInlineCursorAnchor, {
  handleTrailingInlineCursorKeyDown,
  moveCursorBeforeTrailingCursor,
} from "@/features/chat/editor/TrailingInlineCursorAnchor";
import { getQfaceLabel, getQfaceUrl } from "@/features/chat/emoji";
import { useAssetsStore } from "@/stores/assets.store";
import { parseClipboardHtmlToContent } from "@/features/chat/editor/clipboard";
import {
  collectChatSegmentsFromComposerDoc,
  type ComposerNode,
} from "@/features/chat/editor/chatSegmentCodec";

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }
      reject(new Error("Failed to read clipboard image"));
    };
    reader.onerror = () => {
      reject(reader.error ?? new Error("Failed to read clipboard image"));
    };
    reader.readAsDataURL(file);
  });
}

const emit = defineEmits<{
  "can-send-change": [value: boolean];
  "submit-request": [];
}>();

const editorVersion = ref(0);
const assetsStore = useAssetsStore();

function syncEditorState() {
  editorVersion.value += 1;
}

function insertQfaceById(qfaceId: string) {
  const src = assetsStore.getAssetDisplayUrl("qface", qfaceId) || getQfaceUrl(qfaceId);
  if (!src || !editor.value) return;

  moveCursorBeforeTrailingCursor(editor.value);

  editor.value
    .chain()
    .focus()
    .insertContent({
      type: "inlineEmoji",
      attrs: {
        src,
        alt: getQfaceLabel(qfaceId),
        kind: "emoji",
        emojiId: qfaceId,
      },
    })
    .run();

  syncEditorState();
}

function insertText(text: string) {
  if (!text || !editor.value) return;

  moveCursorBeforeTrailingCursor(editor.value);
  editor.value
    .chain()
    .focus()
    .insertContent(text)
    .run();

  syncEditorState();
}

function insertSticker(sticker: {
  id: number;
  url: string;
  alt?: string;
}) {
  if (!editor.value || !sticker.url) return;

  moveCursorBeforeTrailingCursor(editor.value);

  editor.value
    .chain()
    .focus()
    .insertContent({
      type: "inlineMedia",
      attrs: {
        src: sticker.url,
        alt: sticker.alt || `Sticker ${sticker.id}`,
        kind: "sticker",
        assetId: String(sticker.id),
      },
    })
    .run();

  syncEditorState();
}

function collectSegments() {
  if (!editor.value) return [];

  const json = editor.value.getJSON() as ComposerNode;
  return collectChatSegmentsFromComposerDoc(json);
}

function clearAndFocus() {
  if (!editor.value) return;
  editor.value.commands.clearContent(true);
  editor.value.commands.focus();
  syncEditorState();
}

async function insertClipboardImages(files: File[]) {
  if (!editor.value || files.length === 0) return;

  const resolvedImages = await Promise.all(
    files.map(async (file, index) => ({
      src: await readFileAsDataUrl(file),
      alt: file.name || `Pasted image ${index + 1}`,
    })),
  );

  const content = resolvedImages.map((image) => ({
    type: "inlineMedia",
    attrs: {
      src: image.src,
      alt: image.alt,
      kind: "image",
    },
  }));

  editor.value
    .chain()
    .focus()
    .insertContent(content)
    .run();

  syncEditorState();
}

const editor = useEditor({
  extensions: [
    TrailingInlineCursorAnchor,
    StarterKit.configure({
      heading: false,
      bulletList: false,
      orderedList: false,
      listItem: false,
      blockquote: false,
      codeBlock: false,
      horizontalRule: false,
    }),
    InlineEmoji,
    InlineMedia,
  ],
  content: {
    type: "doc",
    content: [
      {
        type: "paragraph",
      },
    ],
  },
  editorProps: {
    attributes: {
      class: "tiptapEditor",
      role: "textbox",
      "aria-multiline": "true",
    },
    handlePaste: (_view, event) => {
      const clipboardData = event.clipboardData;
      if (!clipboardData) return false;

      const html = clipboardData.getData("text/html");

      const mediaContent = parseClipboardHtmlToContent(
        html,
      );

      if (mediaContent && editor.value) {
        editor.value
          .chain()
          .focus()
          .insertContent(mediaContent)
          .run();
        syncEditorState();
        return true;
      }

      const imageFiles = Array.from(clipboardData.items)
        .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
        .map((item) => item.getAsFile())
        .filter((file): file is File => Boolean(file));

      if (imageFiles.length === 0) {
        return false;
      }

      void insertClipboardImages(imageFiles);
      return true;
    },
    handleKeyDown: (_view, event) => {
      if (!editor.value) return false;
      if (event.isComposing) return false;

      if (event.key === "Enter" && !event.shiftKey && !event.altKey) {
        event.preventDefault();
        emit("submit-request");
        return true;
      }

      return handleTrailingInlineCursorKeyDown(editor.value, event);
    },
  },
  onUpdate: () => {
    syncEditorState();
  },
});

const canSend = computed(() => {
  editorVersion.value;
  return collectSegments().length > 0;
});

watch(
  canSend,
  (value) => {
    emit("can-send-change", value);
  },
  { immediate: true },
);

defineExpose({
  insertQfaceById,
  insertSticker,
  insertText,
  collectSegments,
  clearAndFocus,
});

onBeforeUnmount(() => {
  editor.value?.destroy();
});
</script>

<template>
  <div class="inputRow">
    <EditorContent v-if="editor" :editor="editor" class="field" />
  </div>
</template>

<style scoped>
.inputRow {
  display: grid;
}

.field {
  min-height: 72px;
  max-height: 196px;
  border-radius: 14px;
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text);
  font-size: 13px;
  outline: none;
}

.field:focus-within {
  border-color: color-mix(in srgb, var(--c-primary) 26%, var(--c-border));
}

.field :deep(.tiptapEditor) {
  min-height: 72px;
  max-height: 196px;
  padding: 12px 14px;
  outline: none;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
}

.field :deep(.tiptapEditor p) {
  margin: 0;
}

.field :deep(.tiptapEditor::selection) {
  background: rgb(59 130 246 / 0.28);
}

.field :deep(.tiptapEditor *)::selection {
  background: rgb(59 130 246 / 0.28);
}

.field :deep(.tiptapEditor .chatInlineMedia--editor) {
  margin: 4px;
}

.field :deep(.tiptapEditor .chatInlineMedia--editor.chatInlineMedia--emoji) {
  margin: 0;
}

.field :deep(.tiptapEditor .chatInlineMedia--selected-range),
.field :deep(.tiptapEditor .chatInlineMedia--selected-node) {
  isolation: isolate;
}
</style>
