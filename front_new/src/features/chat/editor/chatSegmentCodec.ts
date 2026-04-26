import {
  chatTextHasVisibleCharacters,
  trimTrailingInvisibleTextSegments,
} from "@/features/chat/segments";
import type { ChatSegment } from "@/features/chat/types";
import { stripInlineCursorAnchors } from "./TrailingInlineCursorAnchor";

export type ComposerNode = {
  type?: string;
  text?: string;
  attrs?: Record<string, unknown>;
  content?: ComposerNode[];
};

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
      type: "media",
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

export function collectChatSegmentsFromComposerDoc(json: ComposerNode) {
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
