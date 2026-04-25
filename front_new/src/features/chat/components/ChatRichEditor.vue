<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { EditorContent, useEditor } from "@tiptap/vue-3";
import StarterKit from "@tiptap/starter-kit";
import InlineMedia from "@/features/chat/editor/InlineMedia";
import InlineEmoji from "@/features/chat/editor/InlineEmoji";
import TrailingInlineCursorAnchor, {
  handleTrailingInlineCursorKeyDown,
  moveCursorBeforeTrailingCursor,
  stripInlineCursorAnchors,
} from "@/features/chat/editor/TrailingInlineCursorAnchor";
import { getQfaceLabel, getQfaceUrl } from "@/features/chat/emoji";
import {
  chatTextHasVisibleCharacters,
  trimTrailingInvisibleTextSegments,
} from "@/features/chat/segments";
import type { ChatSegment } from "@/features/chat/types";

type ComposerNode = {
  type?: string;
  text?: string;
  attrs?: Record<string, unknown>;
  content?: ComposerNode[];
};

type EditorInsertNode =
  | { type: "text"; text: string }
  | { type: "hardBreak" }
  | {
    type: "inlineEmoji";
    attrs: {
      src: string;
      alt: string;
      kind: "emoji";
      emojiId: string;
      animated: boolean;
    };
  }
  | {
    type: "inlineMedia";
    attrs: {
      src: string;
      alt: string;
      kind: "image" | "sticker";
      assetId: string | null;
      animated: boolean;
    };
  };

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

function appendEditorInsertText(target: EditorInsertNode[], text: string) {
  if (!text) return;

  const previous = target[target.length - 1];
  if (previous?.type === "text") {
    previous.text += text;
    return;
  }

  target.push({
    type: "text",
    text,
  });
}

function appendEditorHardBreak(target: EditorInsertNode[]) {
  const previous = target[target.length - 1];
  if (previous?.type === "hardBreak") return;

  target.push({ type: "hardBreak" });
}

function normalizeEditorInsertNodes(nodes: EditorInsertNode[]) {
  const normalized: EditorInsertNode[] = [];

  nodes.forEach((node) => {
    if (node.type === "text") {
      appendEditorInsertText(normalized, node.text);
      return;
    }

    if (node.type === "hardBreak") {
      appendEditorHardBreak(normalized);
      return;
    }

    normalized.push(node);
  });

  while (normalized[0]?.type === "hardBreak") {
    normalized.shift();
  }

  while (normalized[normalized.length - 1]?.type === "hardBreak") {
    normalized.pop();
  }

  return normalized;
}

function parseClipboardMediaImage(image: HTMLImageElement): EditorInsertNode[] {
  const kind = image.getAttribute("data-kind");
  const src = image.getAttribute("src") ?? undefined;
  const alt = image.getAttribute("alt") ?? undefined;
  const animated = image.getAttribute("data-animated") === "true";

  if (kind === "emoji") {
    const emojiId = image.getAttribute("data-emoji-id");
    if (!emojiId || !src) return [];

    return [{
      type: "inlineEmoji",
      attrs: {
        src,
        alt: alt || "",
        kind: "emoji",
        emojiId,
        animated,
      },
    }];
  }

  if (kind !== "image" && kind !== "sticker") return [];
  if (!src) return [];

  return [{
    type: "inlineMedia",
    attrs: {
      src,
      alt: alt || (kind === "sticker" ? "Sticker" : "Image"),
      kind,
      assetId: image.getAttribute("data-asset-id"),
      animated,
    },
  }];
}

function walkClipboardNode(node: Node, target: EditorInsertNode[]) {
  if (node.nodeType === Node.TEXT_NODE) {
    appendEditorInsertText(target, node.textContent ?? "");
    return;
  }

  if (!(node instanceof HTMLElement)) {
    return;
  }

  if (node.tagName === "BR") {
    appendEditorHardBreak(target);
    return;
  }

  if (node.tagName === "IMG" && node.hasAttribute("data-kind")) {
    target.push(...parseClipboardMediaImage(node as HTMLImageElement));
    return;
  }

  const isBlockLike = /^(P|DIV|LI|UL|OL|BLOCKQUOTE|PRE)$/.test(node.tagName);
  const beforeLength = target.length;

  Array.from(node.childNodes).forEach((child) => {
    walkClipboardNode(child, target);
  });

  if (isBlockLike && target.length > beforeLength) {
    appendEditorHardBreak(target);
  }
}

function parseClipboardHtmlToContent(html: string) {
  if (!html || typeof DOMParser === "undefined") return null;

  const startFragment = "<!--StartFragment-->";
  const endFragment = "<!--EndFragment-->";
  const fragmentStart = html.indexOf(startFragment);
  const fragmentEnd = html.indexOf(endFragment);
  const htmlToParse = fragmentStart >= 0 && fragmentEnd > fragmentStart
    ? html.slice(fragmentStart + startFragment.length, fragmentEnd)
    : html;

  const documentFragment = new DOMParser().parseFromString(htmlToParse, "text/html");
  const content: EditorInsertNode[] = [];

  Array.from(documentFragment.body.childNodes).forEach((node) => {
    walkClipboardNode(node, content);
  });

  const normalized = normalizeEditorInsertNodes(content);
  return normalized.length > 0 ? normalized : null;
}

const emit = defineEmits<{
  "can-send-change": [value: boolean];
  "submit-request": [];
}>();

const editorVersion = ref(0);

function syncEditorState() {
  editorVersion.value += 1;
}

function insertQfaceById(qfaceId: string) {
  const src = getQfaceUrl(qfaceId);
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

function appendTextBuffer(
  target: ChatSegment[],
  textBuffer: string[],
  options: { preserveInvisibleText?: boolean } = {},
) {
  const rawContent = textBuffer.join("");
  const content = stripInlineCursorAnchors(rawContent)
    .replace(/\u00a0/g, " ");
  const hasVisibleText = chatTextHasVisibleCharacters(content);
  const hasAnyText = content.length > 0;

  if (!hasVisibleText && !(options.preserveInvisibleText && hasAnyText)) {
    textBuffer.length = 0;
    return;
  }

  target.push({
    id: `text-${Date.now()}-${target.length}`,
    type: "text",
    content,
  });
  textBuffer.length = 0;
}

function collectSegmentsFromNode(
  node: ComposerNode,
  target: ChatSegment[],
  textBuffer: string[],
) {
  if (node.type === "text" && typeof node.text === "string") {
    textBuffer.push(node.text);
    return;
  }

  if (node.type === "hardBreak") {
    textBuffer.push("\n");
    return;
  }

  if (node.type === "inlineEmoji") {
    const attrs = node.attrs ?? {};
    const emojiId = typeof attrs.emojiId === "string" ? attrs.emojiId : undefined;
    if (!emojiId) return;

    appendTextBuffer(target, textBuffer, { preserveInvisibleText: true });
    target.push({
      id: `emoji-${Date.now()}-${target.length}`,
      type: "emoji",
      emojiId,
      animated: Boolean(attrs.animated),
    });
    return;
  }

  if (node.type === "inlineMedia" || node.type === "image") {
    const attrs = node.attrs ?? {};
    const src = typeof attrs.src === "string" ? attrs.src : undefined;
    const kind = attrs.kind === "sticker" ? "sticker" : "image";
    if (!src) return;

    appendTextBuffer(target, textBuffer, { preserveInvisibleText: true });
    target.push({
      id: `media-${Date.now()}-${target.length}`,
      type: "image",
      alt: typeof attrs.alt === "string" ? attrs.alt : "Image",
      src,
      kind,
      assetId: typeof attrs.assetId === "string" ? attrs.assetId : undefined,
      animated: Boolean(attrs.animated),
    });
    return;
  }

  node.content?.forEach((child) => {
    collectSegmentsFromNode(child, target, textBuffer);
  });
}

function collectSegments() {
  if (!editor.value) return [];

  const json = editor.value.getJSON() as ComposerNode;
  const segments: ChatSegment[] = [];
  const textBuffer: string[] = [];

  json.content?.forEach((node, index) => {
    collectSegmentsFromNode(node, segments, textBuffer);

    if (node.type === "paragraph" && index < (json.content?.length ?? 0) - 1) {
      textBuffer.push("\n");
    }
  });

  appendTextBuffer(segments, textBuffer);

  trimTrailingInvisibleTextSegments(segments);

  return segments;
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
