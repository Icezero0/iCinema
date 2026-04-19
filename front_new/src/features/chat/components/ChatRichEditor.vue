<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { EditorContent, useEditor } from "@tiptap/vue-3";
import { Extension } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { NodeSelection, Plugin, TextSelection } from "@tiptap/pm/state";
import InlineMedia from "@/features/chat/editor/InlineMedia";
import InlineEmoji from "@/features/chat/editor/InlineEmoji";
import { getChatEmojiLabel, getChatEmojiUrl } from "@/features/chat/emoji";
import type { ChatSegment } from "@/features/chat/types";

type ComposerNode = {
  type?: string;
  text?: string;
  attrs?: Record<string, unknown>;
  content?: ComposerNode[];
};

const TRAILING_CURSOR_TEXT = "\u200B";
const INLINE_TAIL_POLICIES = {
  inlineMedia: { selectable: true },
  inlineEmoji: { selectable: false },
} as const;

type InlineTailNodeName = keyof typeof INLINE_TAIL_POLICIES;

function isInlineTailNodeName(name: string): name is InlineTailNodeName {
  return name in INLINE_TAIL_POLICIES;
}

function getInlineTailPolicy(name: string) {
  return isInlineTailNodeName(name) ? INLINE_TAIL_POLICIES[name] : null;
}

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

function moveCursorBeforeTrailingCursor(editor: any) {
  const { state, view } = editor;
  const selection = state.selection;
  if (!selection.empty) return false;

  const { $from } = selection;
  const before = $from.nodeBefore;
  if (!before?.isText || !before.text?.endsWith(TRAILING_CURSOR_TEXT)) return false;

  const hiddenStartPos = selection.from - before.nodeSize;
  const beforeHidden = state.doc.resolve(hiddenStartPos).nodeBefore;
  if (!beforeHidden || !getInlineTailPolicy(beforeHidden.type.name)) return false;

  view.dispatch(state.tr.setSelection(TextSelection.create(state.doc, hiddenStartPos)));
  return true;
}

function moveAcrossTrailingCursor(
  editor: any,
  direction: "left" | "right",
  extendSelection = false,
) {
  const { state, view } = editor;
  const selection = state.selection;
  if (!selection.empty) return false;

  const { $from } = selection;

  if (direction === "right") {
    const after = $from.nodeAfter;
    if (!after?.isText || !after.text?.startsWith(TRAILING_CURSOR_TEXT)) return false;

    const nextPos = selection.from + 1;
    const nextSelection = extendSelection
      ? TextSelection.create(state.doc, selection.from, nextPos)
      : TextSelection.create(state.doc, nextPos);
    view.dispatch(state.tr.setSelection(nextSelection));
    return true;
  }

  const before = $from.nodeBefore;
  if (!before?.isText || !before.text?.endsWith(TRAILING_CURSOR_TEXT)) return false;

  const hiddenStartPos = selection.from - before.nodeSize;
  const beforeHidden = state.doc.resolve(hiddenStartPos).nodeBefore;
  const policy = beforeHidden ? getInlineTailPolicy(beforeHidden.type.name) : null;

  if (beforeHidden && policy && extendSelection) {
    const targetPos = hiddenStartPos - beforeHidden.nodeSize;
    view.dispatch(state.tr.setSelection(TextSelection.create(state.doc, hiddenStartPos, targetPos)));
    return true;
  }

  if (beforeHidden && policy?.selectable) {
    const mediaStartPos = hiddenStartPos - beforeHidden.nodeSize;
    view.dispatch(state.tr.setSelection(NodeSelection.create(state.doc, mediaStartPos)));
    return true;
  }

  if (policy) {
    const targetPos = beforeHidden
      ? hiddenStartPos - beforeHidden.nodeSize
      : hiddenStartPos;
    view.dispatch(state.tr.setSelection(TextSelection.create(state.doc, targetPos)));
    return true;
  }

  view.dispatch(state.tr.setSelection(TextSelection.create(state.doc, hiddenStartPos)));
  return true;
}

function deleteAcrossTrailingCursor(
  editor: any,
  direction: "backspace" | "delete",
) {
  const { state, view } = editor;
  const selection = state.selection;
  if (!selection.empty) return false;

  const { $from } = selection;

  if (direction === "backspace") {
    const before = $from.nodeBefore;
    if (!before?.isText || !before.text?.endsWith(TRAILING_CURSOR_TEXT)) return false;

    const cursorPos = selection.from;
    const anchorStartPos = cursorPos - before.nodeSize;
    const beforeAnchor = state.doc.resolve(anchorStartPos).nodeBefore;
    if (!beforeAnchor || !getInlineTailPolicy(beforeAnchor.type.name)) return false;

    const targetStartPos = anchorStartPos - beforeAnchor.nodeSize;
    view.dispatch(state.tr.delete(targetStartPos, cursorPos));
    return true;
  }

  const after = $from.nodeAfter;
  if (!after?.isText || !after.text?.startsWith(TRAILING_CURSOR_TEXT)) return false;

  const cursorPos = selection.from;
  const beforeAnchor = state.doc.resolve(cursorPos).nodeBefore;
  if (!beforeAnchor || !getInlineTailPolicy(beforeAnchor.type.name)) return false;

  const targetStartPos = cursorPos - beforeAnchor.nodeSize;
  view.dispatch(state.tr.delete(targetStartPos, cursorPos + after.nodeSize));
  return true;
}

const TrailingInlineTailAnchor = Extension.create({
  name: "trailingInlineTailAnchor",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        appendTransaction: (_transactions, _oldState, newState) => {
          const { doc, tr } = newState;
          let changed = false;

          doc.descendants((node, pos, parent, index) => {
            if (!parent || typeof index !== "number" || parent.type.name !== "paragraph") return;

            if (getInlineTailPolicy(node.type.name)) {
              if (index !== parent.childCount - 1) {
                return;
              }

              const insertPos = pos + node.nodeSize;
              const afterNode = doc.resolve(insertPos).nodeAfter;
              if (afterNode?.isText && afterNode.text?.startsWith(TRAILING_CURSOR_TEXT)) {
                return;
              }

              tr.insertText(TRAILING_CURSOR_TEXT, insertPos);
              changed = true;
              return;
            }

            if (!node.isText || !node.text?.includes(TRAILING_CURSOR_TEXT)) return;

            const previousSibling = index > 0 ? parent.child(index - 1) : null;
            const isAfterTerminalMedia =
              Boolean(previousSibling && getInlineTailPolicy(previousSibling.type.name)) &&
              index - 1 === parent.childCount - 2 &&
              node.text === TRAILING_CURSOR_TEXT;

            if (isAfterTerminalMedia) return;

            const cleanedText = node.text.replace(/\u200B/g, "");
            if (cleanedText === node.text) return;

            tr.insertText(cleanedText, pos, pos + node.nodeSize);
            changed = true;
          });

          return changed ? tr : null;
        },
      }),
    ];
  },
});

const emit = defineEmits<{
  "can-send-change": [value: boolean];
}>();

const editorVersion = ref(0);

function syncEditorState() {
  editorVersion.value += 1;
}

function insertEmojiById(emojiId: string) {
  const src = getChatEmojiUrl(emojiId);
  if (!src || !editor.value) return;

  moveCursorBeforeTrailingCursor(editor.value);

  editor.value
    .chain()
    .focus()
    .insertContent({
      type: "inlineEmoji",
      attrs: {
        src,
        alt: getChatEmojiLabel(emojiId),
        kind: "emoji",
        emojiId,
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

function appendTextBuffer(target: ChatSegment[], textBuffer: string[]) {
  const content = textBuffer.join("")
    .replace(/\u200B/g, "")
    .replace(/\u00a0/g, " ");

  if (!content.trim()) {
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

    appendTextBuffer(target, textBuffer);
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

    appendTextBuffer(target, textBuffer);
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
    TrailingInlineTailAnchor,
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

      const imageFiles = Array.from(clipboardData.items)
        .filter((item) => item.kind === "file" && item.type.startsWith("image/"))
        .map((item) => item.getAsFile())
        .filter((file): file is File => Boolean(file));

      if (imageFiles.length === 0) return false;

      void insertClipboardImages(imageFiles);
      return true;
    },
    handleKeyDown: (_view, event) => {
      if (!editor.value) return false;

      if (event.key === "ArrowRight" && moveAcrossTrailingCursor(editor.value, "right", event.shiftKey)) {
        event.preventDefault();
        return true;
      }

      if (event.key === "ArrowLeft" && moveAcrossTrailingCursor(editor.value, "left", event.shiftKey)) {
        event.preventDefault();
        return true;
      }

      if (event.key === "Backspace" && deleteAcrossTrailingCursor(editor.value, "backspace")) {
        event.preventDefault();
        return true;
      }

      if (event.key === "Delete" && deleteAcrossTrailingCursor(editor.value, "delete")) {
        event.preventDefault();
        return true;
      }

      return false;
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
  insertEmojiById,
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
