import type { ChatSegment } from "@/features/chat/types";

const INLINE_CURSOR_ANCHOR_PATTERN = /\u200B/g;

export function stripChatTextCursorAnchors(content: string) {
  return content.replace(INLINE_CURSOR_ANCHOR_PATTERN, "");
}

export function chatTextHasVisibleCharacters(content: string) {
  return stripChatTextCursorAnchors(content).trim().length > 0;
}

export function trimTrailingInvisibleTextSegments(segments: ChatSegment[]) {
  while (segments.length > 0) {
    const lastSegment = segments[segments.length - 1];
    if (lastSegment?.type !== "text") break;

    const contentWithoutAnchors = stripChatTextCursorAnchors(lastSegment.content);
    const trimmedContent = contentWithoutAnchors.trimEnd();

    if (!trimmedContent) {
      segments.pop();
      continue;
    }

    lastSegment.content = trimmedContent;
    break;
  }

  return segments;
}
