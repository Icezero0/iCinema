import { computed, onBeforeUnmount, onMounted, ref, type Ref } from "vue";

type ChatMediaKind = "emoji" | "image" | "sticker";
type ChatMediaContext = "editor" | "message";
type SelectionSubscriber = () => void;
type CopySubscriber = (event: ClipboardEvent) => void;

const selectionSubscribers = new Set<SelectionSubscriber>();
const copySubscribers = new Set<CopySubscriber>();

function notifySelectionSubscribers() {
  selectionSubscribers.forEach((callback) => callback());
}

function notifyCopySubscribers(event: ClipboardEvent) {
  copySubscribers.forEach((callback) => callback(event));
}

function subscribeSelectionChange(callback: SelectionSubscriber) {
  if (selectionSubscribers.size === 0 && typeof document !== "undefined") {
    document.addEventListener("selectionchange", notifySelectionSubscribers);
  }

  selectionSubscribers.add(callback);

  return () => {
    selectionSubscribers.delete(callback);

    if (selectionSubscribers.size === 0 && typeof document !== "undefined") {
      document.removeEventListener("selectionchange", notifySelectionSubscribers);
    }
  };
}

function subscribeCopy(callback: CopySubscriber) {
  if (copySubscribers.size === 0 && typeof document !== "undefined") {
    document.addEventListener("copy", notifyCopySubscribers);
  }

  copySubscribers.add(callback);

  return () => {
    copySubscribers.delete(callback);

    if (copySubscribers.size === 0 && typeof document !== "undefined") {
      document.removeEventListener("copy", notifyCopySubscribers);
    }
  };
}

function getNodeIndex(node: Node) {
  const parent = node.parentNode;
  if (!parent) return -1;
  return Array.prototype.indexOf.call(parent.childNodes, node);
}

type UseChatMediaSelectionOptions = {
  rootRef: Ref<HTMLElement | null>;
  context: Ref<ChatMediaContext>;
  kind: Ref<ChatMediaKind>;
  src: Ref<string | undefined>;
  alt: Ref<string>;
  assetId: Ref<string | null | undefined>;
  emojiId: Ref<string | undefined>;
  animated: Ref<boolean>;
  selectedRange: Ref<boolean>;
  selectedNode: Ref<boolean>;
};

export function useChatMediaSelection(options: UseChatMediaSelectionOptions) {
  const {
    rootRef,
    context,
    kind,
    src,
    alt,
    assetId,
    emojiId,
    animated,
    selectedRange,
    selectedNode,
  } = options;

  const domSelectedRange = ref(false);
  const domSelectedNode = ref(false);
  const domExactlySelected = ref(false);
  let removeSelectionSubscription: (() => void) | null = null;
  let removeCopySubscription: (() => void) | null = null;

  const supportsNodeSelection = computed(
    () => context.value === "message" && kind.value !== "emoji",
  );

  const mergedSelectedRange = computed(
    () => selectedRange.value || domSelectedRange.value,
  );

  const mergedSelectedNode = computed(
    () => selectedNode.value || domSelectedNode.value,
  );

  function syncDomSelectionState() {
    if (context.value !== "message") {
      domSelectedRange.value = false;
      domSelectedNode.value = false;
      domExactlySelected.value = false;
      return;
    }

    const root = rootRef.value;
    const selection = window.getSelection();
    if (!root || !selection || selection.rangeCount === 0 || selection.isCollapsed) {
      domSelectedRange.value = false;
      domSelectedNode.value = false;
      domExactlySelected.value = false;
      return;
    }

    const range = selection.getRangeAt(0);
    const nodeRange = document.createRange();
    nodeRange.selectNode(root);
    domSelectedRange.value =
      range.compareBoundaryPoints(Range.START_TO_START, nodeRange) <= 0 &&
      range.compareBoundaryPoints(Range.END_TO_END, nodeRange) >= 0;

    domExactlySelected.value =
      range.compareBoundaryPoints(Range.START_TO_START, nodeRange) === 0 &&
      range.compareBoundaryPoints(Range.END_TO_END, nodeRange) === 0;

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

    if (domSelectedNode.value) {
      domSelectedRange.value = false;
    }
  }

  function selectMessageNode() {
    if (context.value !== "message") return;

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
      context.value !== "message" ||
      !src.value ||
      !event.clipboardData
    ) {
      return;
    }

    const shouldCopyAsSingleMedia =
      mergedSelectedNode.value ||
      (kind.value === "emoji" && domExactlySelected.value);

    if (!shouldCopyAsSingleMedia) {
      return;
    }

    const escapedAlt = alt.value.replace(/"/g, "&quot;");
    const escapedSrc = src.value.replace(/"/g, "&quot;");
    const assetIdAttr = assetId.value ? ` data-asset-id="${assetId.value}"` : "";
    const emojiIdAttr = emojiId.value ? ` data-emoji-id="${emojiId.value}"` : "";
    const animatedAttr = animated.value ? ` data-animated="true"` : "";
    const html = `<img src="${escapedSrc}" alt="${escapedAlt}" data-kind="${kind.value}"${assetIdAttr}${emojiIdAttr}${animatedAttr}>`;

    event.clipboardData.setData("text/html", html);
    event.clipboardData.setData("text/plain", alt.value);
    event.preventDefault();
  }

  onMounted(() => {
    if (context.value !== "message") return;

    removeSelectionSubscription = subscribeSelectionChange(syncDomSelectionState);
    removeCopySubscription = subscribeCopy(handleDocumentCopy);
  });

  onBeforeUnmount(() => {
    if (context.value !== "message") return;

    removeSelectionSubscription?.();
    removeSelectionSubscription = null;
    removeCopySubscription?.();
    removeCopySubscription = null;
  });

  return {
    mergedSelectedRange,
    mergedSelectedNode,
    selectMessageNode,
  };
}
