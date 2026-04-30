<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { NodeViewWrapper, type NodeViewProps } from "@tiptap/vue-3";
import { NodeSelection } from "@tiptap/pm/state";
import ChatInlineMedia from "@/features/chat/components/ChatInlineMedia.vue";

const props = defineProps<NodeViewProps>();

const isCoveredBySelection = ref(false);

const kind = computed(() => String(props.node.attrs.kind || "image"));
const src = computed(() => String(props.node.attrs.src || ""));
const alt = computed(() => String(props.node.attrs.alt || ""));
const emojiId = computed(() => {
  const value = props.node.attrs.emojiId;
  return value == null ? undefined : String(value);
});
const animated = computed(() => Boolean(props.node.attrs.animated));

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

  if (kind.value === "emoji") {
    // For adjacent inline emojis, treat the emoji as selected only when its
    // anchor position falls inside the selection. A plain overlap check makes
    // neighboring emojis light up together.
    isCoveredBySelection.value = nodeStart >= from && nodeStart < to;
    return;
  }

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
    draggable="false"
    contenteditable="false"
  >
    <ChatInlineMedia
      :kind="kind as 'emoji' | 'image' | 'sticker'"
      :src="src"
      :alt="alt"
      :emoji-id="emojiId"
      :animated="animated"
      context="editor"
      :selected-range="isCoveredBySelection"
      :selected-node="selected && kind !== 'emoji'"
    />
  </NodeViewWrapper>
</template>
