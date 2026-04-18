<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = withDefaults(defineProps<{
  kind: "emoji" | "image" | "sticker";
  src?: string;
  alt: string;
  context?: "editor" | "message";
  displayMode?: "inline" | "block";
  selectedRange?: boolean;
  selectedNode?: boolean;
}>(), {
  context: "message",
  displayMode: "inline",
  src: undefined,
  selectedRange: false,
  selectedNode: false,
});

const rootRef = ref<HTMLElement | null>(null);
const domSelectedRange = ref(false);
const domSelectedNode = ref(false);

const supportsNodeSelection = computed(
  () => props.context === "message" && props.kind !== "emoji",
);

const mergedSelectedRange = computed(
  () => props.selectedRange || domSelectedRange.value,
);

const mergedSelectedNode = computed(
  () => props.selectedNode || domSelectedNode.value,
);

function getNodeIndex(node: Node) {
  const parent = node.parentNode;
  if (!parent) return -1;
  return Array.prototype.indexOf.call(parent.childNodes, node);
}

function syncDomSelectionState() {
  if (props.context !== "message") {
    domSelectedRange.value = false;
    domSelectedNode.value = false;
    return;
  }

  const root = rootRef.value;
  const selection = window.getSelection();
  if (!root || !selection || selection.rangeCount === 0 || selection.isCollapsed) {
    domSelectedRange.value = false;
    domSelectedNode.value = false;
    return;
  }

  const range = selection.getRangeAt(0);
  domSelectedRange.value = range.intersectsNode(root);

  if (!supportsNodeSelection.value) {
    domSelectedNode.value = false;
    return;
  }

  const parent = root.parentNode;
  const nodeIndex = getNodeIndex(root);
  domSelectedNode.value =
    nodeIndex >= 0 &&
    selection.rangeCount > 0 &&
    range.startContainer === parent &&
    range.endContainer === parent &&
    range.startOffset === nodeIndex &&
    range.endOffset === nodeIndex + 1;
}

function selectMessageNode() {
  if (!supportsNodeSelection.value) return;

  const root = rootRef.value;
  const selection = window.getSelection();
  if (!root || !selection) return;

  const range = document.createRange();
  range.selectNode(root);
  selection.removeAllRanges();
  selection.addRange(range);
  syncDomSelectionState();
}

function handleDocumentCopy(event: ClipboardEvent) {
  if (
    props.context !== "message" ||
    !supportsNodeSelection.value ||
    !mergedSelectedNode.value ||
    !props.src ||
    !event.clipboardData
  ) {
    return;
  }

  const escapedAlt = props.alt.replace(/"/g, "&quot;");
  const escapedSrc = props.src.replace(/"/g, "&quot;");
  const html = `<img src="${escapedSrc}" alt="${escapedAlt}" data-kind="${props.kind}">`;

  event.clipboardData.setData("text/html", html);
  event.clipboardData.setData("text/plain", props.alt);
  event.preventDefault();
}

onMounted(() => {
  if (props.context !== "message") return;
  document.addEventListener("selectionchange", syncDomSelectionState);
  document.addEventListener("copy", handleDocumentCopy);
});

onBeforeUnmount(() => {
  if (props.context !== "message") return;
  document.removeEventListener("selectionchange", syncDomSelectionState);
  document.removeEventListener("copy", handleDocumentCopy);
});
</script>

<template>
  <span
    ref="rootRef"
    class="chatInlineMedia"
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
  >
    <img
      v-if="props.src"
      class="chatInlineMedia__image"
      :class="[
        `chatInlineMedia__image--${props.kind}`,
        `chatInlineMedia__image--${props.context}`,
      ]"
      :src="props.src"
      :alt="props.alt"
      :data-kind="props.kind"
      draggable="false"
    >
    <span
      v-else
      class="chatInlineMedia__placeholder"
      :class="`chatInlineMedia__placeholder--${props.context}`"
    >
      <span class="chatInlineMedia__label">{{ props.alt }}</span>
    </span>
  </span>
</template>

<style scoped>
.chatInlineMedia {
  position: relative;
  display: inline-flex;
  vertical-align: text-bottom;
  border-radius: 0;
}

.chatInlineMedia--message.chatInlineMedia--block.chatInlineMedia--image,
.chatInlineMedia--message.chatInlineMedia--block.chatInlineMedia--sticker {
  display: block;
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
  max-width: min(100%, 280px);
  height: auto;
  object-fit: contain;
}

.chatInlineMedia__image--message.chatInlineMedia__image--sticker {
  width: auto;
  max-width: min(100%, 160px);
  height: auto;
  object-fit: contain;
  background: color-mix(in srgb, var(--c-surface) 88%, white);
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
</style>
