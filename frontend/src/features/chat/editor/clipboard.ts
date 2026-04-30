export type EditorInsertNode =
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

function getClipboardHtmlFragment(html: string) {
  const startFragment = "<!--StartFragment-->";
  const endFragment = "<!--EndFragment-->";
  const fragmentStart = html.indexOf(startFragment);
  const fragmentEnd = html.indexOf(endFragment);

  return fragmentStart >= 0 && fragmentEnd > fragmentStart
    ? html.slice(fragmentStart + startFragment.length, fragmentEnd)
    : html;
}

export function parseClipboardHtmlToContent(html: string) {
  if (!html || typeof DOMParser === "undefined") return null;

  const documentFragment = new DOMParser().parseFromString(
    getClipboardHtmlFragment(html),
    "text/html",
  );
  const content: EditorInsertNode[] = [];

  Array.from(documentFragment.body.childNodes).forEach((node) => {
    walkClipboardNode(node, content);
  });

  const normalized = normalizeEditorInsertNodes(content);
  return normalized.length > 0 ? normalized : null;
}
