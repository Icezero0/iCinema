<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { EditorContent, useEditor } from "@tiptap/vue-3";
import { Extension } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { NodeSelection, Plugin, TextSelection } from "@tiptap/pm/state";
import InlineMedia from "@/features/chat/editor/InlineMedia";
import InlineEmoji from "@/features/chat/editor/InlineEmoji";
import { getChatEmojiLabel, getChatEmojiUrl } from "@/features/chat/emoji";
import type { ChatSection } from "@/features/chat/types";

type ComposerNode = {
  type?: string;
  text?: string;
  attrs?: Record<string, unknown>;
  content?: ComposerNode[];
};

const TRAILING_CURSOR_TEXT = "\u200B";

function moveAcrossTrailingCursor(
  editor: any,
  direction: "left" | "right",
) {
  const { state, view } = editor;
  const selection = state.selection;
  if (!selection.empty) return false;

  const { $from } = selection;

  if (direction === "right") {
    const after = $from.nodeAfter;
    if (!after?.isText || !after.text?.startsWith(TRAILING_CURSOR_TEXT)) return false;

    const nextPos = selection.from + 1;
    view.dispatch(state.tr.setSelection(TextSelection.create(state.doc, nextPos)));
    return true;
  }

  const before = $from.nodeBefore;
  if (!before?.isText || !before.text?.endsWith(TRAILING_CURSOR_TEXT)) return false;

  const hiddenStartPos = selection.from - before.nodeSize;
  const beforeHidden = state.doc.resolve(hiddenStartPos).nodeBefore;

  if (beforeHidden?.type.name === "inlineMedia") {
    const mediaStartPos = hiddenStartPos - beforeHidden.nodeSize;
    view.dispatch(state.tr.setSelection(NodeSelection.create(state.doc, mediaStartPos)));
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
    const mediaPos = cursorPos - before.nodeSize - 1;
    if (mediaPos < 0) return false;

    const mediaNode = state.doc.nodeAt(mediaPos);
    if (!mediaNode || mediaNode.type.name !== "inlineMedia") return false;

    view.dispatch(state.tr.delete(mediaPos, cursorPos));
    return true;
  }

  const after = $from.nodeAfter;
  if (!after?.isText || !after.text?.startsWith(TRAILING_CURSOR_TEXT)) return false;

  const cursorPos = selection.from;
  const mediaNode = state.doc.nodeAt(cursorPos + after.nodeSize);
  if (!mediaNode || mediaNode.type.name !== "inlineMedia") return false;

  view.dispatch(state.tr.delete(cursorPos, cursorPos + after.nodeSize + mediaNode.nodeSize));
  return true;
}

const TrailingMediaCursor = Extension.create({
  name: "trailingMediaCursor",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        appendTransaction: (_transactions, _oldState, newState) => {
          const { doc, tr } = newState;
          let changed = false;

          doc.descendants((node, pos, parent, index) => {
            if (!parent || typeof index !== "number" || parent.type.name !== "paragraph") return;

            if (node.type.name === "inlineMedia") {
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
              previousSibling?.type.name === "inlineMedia" &&
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

function appendTextBuffer(target: ChatSection[], textBuffer: string[]) {
  const content = textBuffer.join("")
    .replace(/\u200B/g, "")
    .replace(/\u00a0/g, " ")
    .trim();
  if (!content) {
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

function collectSectionsFromNode(
  node: ComposerNode,
  target: ChatSection[],
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
    const kind = typeof attrs.kind === "string" ? attrs.kind : "image";
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

  const isParagraph = node.type === "paragraph";
  if (isParagraph && textBuffer.length > 0) {
    textBuffer.push("\n");
  }

  node.content?.forEach((child) => {
    collectSectionsFromNode(child, target, textBuffer);
  });

  if (isParagraph) {
    textBuffer.push("\n");
  }
}

function collectSections() {
  if (!editor.value) return [];

  const json = editor.value.getJSON() as ComposerNode;
  const sections: ChatSection[] = [];
  const textBuffer: string[] = [];

  json.content?.forEach((node) => {
    collectSectionsFromNode(node, sections, textBuffer);
  });

  appendTextBuffer(sections, textBuffer);
  return sections;
}

function clearAndFocus() {
  if (!editor.value) return;
  editor.value.commands.clearContent(true);
  editor.value.commands.focus();
  syncEditorState();
}

const editor = useEditor({
  extensions: [
    TrailingMediaCursor,
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
    handleKeyDown: (_view, event) => {
      if (!editor.value) return false;

      if (event.key === "ArrowRight" && moveAcrossTrailingCursor(editor.value, "right")) {
        event.preventDefault();
        return true;
      }

      if (event.key === "ArrowLeft" && moveAcrossTrailingCursor(editor.value, "left")) {
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
  return collectSections().length > 0;
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
  collectSections,
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

.field :deep(.tiptapEditor .inlineMediaNode) {
  margin: 4px;
  vertical-align: text-bottom;
}

.field :deep(.tiptapEditor .inlineMediaNode-emoji) {
  margin: 0;
  vertical-align: -0.24em;
}

.field :deep(.tiptapEditor .inlineMediaNode.selectedRange),
.field :deep(.tiptapEditor .inlineMediaNode.selectedNode) {
  isolation: isolate;
}
</style>
