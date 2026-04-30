import { Extension } from "@tiptap/core";
import { NodeSelection, Plugin, TextSelection } from "@tiptap/pm/state";

export const INLINE_CURSOR_ANCHOR_TEXT = "\u200B";

const INLINE_CURSOR_ANCHOR_POLICIES = {
  inlineMedia: { selectable: true },
  inlineEmoji: { selectable: false },
} as const;

type InlineCursorAnchorNodeName = keyof typeof INLINE_CURSOR_ANCHOR_POLICIES;

function isInlineCursorAnchorNodeName(name: string): name is InlineCursorAnchorNodeName {
  return name in INLINE_CURSOR_ANCHOR_POLICIES;
}

function getInlineCursorAnchorPolicy(name: string) {
  return isInlineCursorAnchorNodeName(name)
    ? INLINE_CURSOR_ANCHOR_POLICIES[name]
    : null;
}

function setTextSelection(editor: any, pos: number) {
  const { state, view } = editor;
  view.dispatch(state.tr.setSelection(TextSelection.create(state.doc, pos)));
}

export function stripInlineCursorAnchors(text: string) {
  return text.replace(/\u200B/g, "");
}

export function moveCursorBeforeTrailingCursor(editor: any) {
  const { state } = editor;
  const selection = state.selection;
  if (!selection.empty) return false;

  const { $from } = selection;
  const before = $from.nodeBefore;
  if (!before?.isText || !before.text?.endsWith(INLINE_CURSOR_ANCHOR_TEXT)) {
    return false;
  }

  const hiddenStartPos = selection.from - before.nodeSize;
  const beforeHidden = state.doc.resolve(hiddenStartPos).nodeBefore;
  if (!beforeHidden || !getInlineCursorAnchorPolicy(beforeHidden.type.name)) {
    return false;
  }

  setTextSelection(editor, hiddenStartPos);
  return true;
}

export function moveAcrossTrailingCursor(
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
    if (!after?.isText || !after.text?.startsWith(INLINE_CURSOR_ANCHOR_TEXT)) {
      return false;
    }

    const nextPos = selection.from + 1;
    const nextSelection = extendSelection
      ? TextSelection.create(state.doc, selection.from, nextPos)
      : TextSelection.create(state.doc, nextPos);
    view.dispatch(state.tr.setSelection(nextSelection));
    return true;
  }

  const before = $from.nodeBefore;
  if (!before?.isText || !before.text?.endsWith(INLINE_CURSOR_ANCHOR_TEXT)) {
    return false;
  }

  const hiddenStartPos = selection.from - before.nodeSize;
  const beforeHidden = state.doc.resolve(hiddenStartPos).nodeBefore;
  const policy = beforeHidden
    ? getInlineCursorAnchorPolicy(beforeHidden.type.name)
    : null;

  if (beforeHidden && policy && extendSelection) {
    const targetPos = hiddenStartPos - beforeHidden.nodeSize;
    view.dispatch(state.tr.setSelection(
      TextSelection.create(state.doc, hiddenStartPos, targetPos),
    ));
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

  setTextSelection(editor, hiddenStartPos);
  return true;
}

export function deleteAcrossTrailingCursor(
  editor: any,
  direction: "backspace" | "delete",
) {
  const { state, view } = editor;
  const selection = state.selection;
  if (!selection.empty) return false;

  const { $from } = selection;

  if (direction === "backspace") {
    const before = $from.nodeBefore;
    if (!before?.isText || !before.text?.endsWith(INLINE_CURSOR_ANCHOR_TEXT)) {
      return false;
    }

    const cursorPos = selection.from;
    const anchorStartPos = cursorPos - before.nodeSize;
    const beforeAnchor = state.doc.resolve(anchorStartPos).nodeBefore;
    if (!beforeAnchor || !getInlineCursorAnchorPolicy(beforeAnchor.type.name)) {
      return false;
    }

    const targetStartPos = anchorStartPos - beforeAnchor.nodeSize;
    view.dispatch(state.tr.delete(targetStartPos, cursorPos));
    return true;
  }

  const after = $from.nodeAfter;
  if (!after?.isText || !after.text?.startsWith(INLINE_CURSOR_ANCHOR_TEXT)) {
    return false;
  }

  const cursorPos = selection.from;
  const beforeAnchor = state.doc.resolve(cursorPos).nodeBefore;
  if (!beforeAnchor || !getInlineCursorAnchorPolicy(beforeAnchor.type.name)) {
    return false;
  }

  const targetStartPos = cursorPos - beforeAnchor.nodeSize;
  view.dispatch(state.tr.delete(targetStartPos, cursorPos + after.nodeSize));
  return true;
}

export function handleTrailingInlineCursorKeyDown(editor: any, event: KeyboardEvent) {
  if (event.key === "ArrowRight" && moveAcrossTrailingCursor(editor, "right", event.shiftKey)) {
    event.preventDefault();
    return true;
  }

  if (event.key === "ArrowLeft" && moveAcrossTrailingCursor(editor, "left", event.shiftKey)) {
    event.preventDefault();
    return true;
  }

  if (event.key === "Backspace" && deleteAcrossTrailingCursor(editor, "backspace")) {
    event.preventDefault();
    return true;
  }

  if (event.key === "Delete" && deleteAcrossTrailingCursor(editor, "delete")) {
    event.preventDefault();
    return true;
  }

  return false;
}

const TrailingInlineCursorAnchor = Extension.create({
  name: "trailingInlineCursorAnchor",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        appendTransaction: (_transactions, _oldState, newState) => {
          const { doc, tr } = newState;
          let changed = false;

          doc.descendants((node, pos, parent, index) => {
            if (!parent || typeof index !== "number" || parent.type.name !== "paragraph") {
              return;
            }

            if (getInlineCursorAnchorPolicy(node.type.name)) {
              if (index !== parent.childCount - 1) return;

              const insertPos = pos + node.nodeSize;
              const afterNode = doc.resolve(insertPos).nodeAfter;
              if (
                afterNode?.isText &&
                afterNode.text?.startsWith(INLINE_CURSOR_ANCHOR_TEXT)
              ) {
                return;
              }

              tr.insertText(INLINE_CURSOR_ANCHOR_TEXT, insertPos);
              changed = true;
              return;
            }

            if (!node.isText || !node.text?.includes(INLINE_CURSOR_ANCHOR_TEXT)) {
              return;
            }

            const previousSibling = index > 0 ? parent.child(index - 1) : null;
            const isAfterTerminalMedia =
              Boolean(
                previousSibling &&
                getInlineCursorAnchorPolicy(previousSibling.type.name),
              ) &&
              index - 1 === parent.childCount - 2 &&
              node.text === INLINE_CURSOR_ANCHOR_TEXT;

            if (isAfterTerminalMedia) return;

            const cleanedText = stripInlineCursorAnchors(node.text);
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

export default TrailingInlineCursorAnchor;
