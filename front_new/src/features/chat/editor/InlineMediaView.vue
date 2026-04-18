<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { NodeViewWrapper, type NodeViewProps } from "@tiptap/vue-3";
import { NodeSelection } from "@tiptap/pm/state";

const props = defineProps<NodeViewProps>();

const isCoveredBySelection = ref(false);

const kind = computed(() => String(props.node.attrs.kind || "image"));
const src = computed(() => String(props.node.attrs.src || ""));
const alt = computed(() => String(props.node.attrs.alt || ""));
const emojiId = computed(() => {
  const value = props.node.attrs.emojiId;
  return value == null ? "" : String(value);
});

function syncSelectionState() {
  const position = typeof props.getPos === "function" ? props.getPos() : null;
  if (typeof position !== "number") {
    isCoveredBySelection.value = false;
    return;
  }

  const selection = props.editor.state.selection;
  if (selection.empty || selection instanceof NodeSelection) {
    isCoveredBySelection.value = false;
    return;
  }

  const from = selection.from;
  const to = selection.to;
  const nodeStart = position;
  const nodeEnd = position + props.node.nodeSize;

  isCoveredBySelection.value = from <= nodeStart && to >= nodeEnd;
}

onMounted(() => {
  syncSelectionState();
  props.editor.on("selectionUpdate", syncSelectionState);
});

onBeforeUnmount(() => {
  props.editor.off("selectionUpdate", syncSelectionState);
});
</script>

<template>
  <NodeViewWrapper
    as="span"
    class="inlineMediaNode"
    :class="[
      `inlineMediaNode-${kind}`,
      { selectedRange: isCoveredBySelection, selectedNode: selected && kind !== 'emoji' },
    ]"
    contenteditable="false"
  >
    <img
      class="inlineMediaImage"
      :class="`inlineMediaImage-${kind}`"
      :src="src"
      :alt="alt"
      :data-kind="kind"
      :data-emoji-id="emojiId || null"
    >
  </NodeViewWrapper>
</template>

<style scoped>
.inlineMediaNode {
  position: relative;
  display: inline-flex;
  vertical-align: text-bottom;
  border-radius: 0;
}

.inlineMediaNode-emoji {
  border-radius: 0;
}

.inlineMediaNode.selectedRange::after {
  content: "";
  position: absolute;
  inset: -0.05em;
  border-radius: 0;
  background: rgb(59 130 246 / 0.28);
  pointer-events: none;
}

.inlineMediaNode.selectedNode::after {
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

.inlineMediaImage {
  display: block;
  width: 92px;
  height: 92px;
  object-fit: cover;
  border-radius: 12px;
  border: 1px solid color-mix(in srgb, var(--c-primary) 18%, var(--c-border));
}

.inlineMediaImage-emoji {
  width: 1.35em;
  height: 1.35em;
  border: 0;
  border-radius: 0;
  margin: 0 0.12em 0 0.08em;
  background: transparent;
  object-fit: contain;
}

.inlineMediaImage-sticker {
  width: 110px;
  height: 110px;
  object-fit: contain;
  background: color-mix(in srgb, var(--c-surface) 88%, white);
}
</style>
