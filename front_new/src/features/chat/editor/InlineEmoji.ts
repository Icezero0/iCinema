import Image from "@tiptap/extension-image";
import { VueNodeViewRenderer } from "@tiptap/vue-3";
import InlineMediaView from "./InlineMediaView.vue";

const InlineEmoji = Image.extend({
  name: "inlineEmoji",
  selectable: false,

  inline() {
    return true;
  },

  group() {
    return "inline";
  },

  parseHTML() {
    return [
      {
        tag: 'img[data-kind="emoji"][data-emoji-id]',
      },
    ];
  },

  addAttributes() {
    return {
      ...this.parent?.(),
      kind: {
        default: "emoji",
        parseHTML: () => "emoji",
        renderHTML: () => ({
          "data-kind": "emoji",
        }),
      },
      emojiId: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute("data-emoji-id"),
        renderHTML: (attributes: Record<string, unknown>) => {
          if (!attributes.emojiId) return {};
          return { "data-emoji-id": String(attributes.emojiId) };
        },
      },
      animated: {
        default: false,
        parseHTML: (element: HTMLElement) => element.getAttribute("data-animated") === "true",
        renderHTML: (attributes: Record<string, unknown>) => {
          if (!attributes.animated) return {};
          return { "data-animated": "true" };
        },
      },
    };
  },

  addNodeView() {
    return VueNodeViewRenderer(InlineMediaView);
  },
}).configure({
  allowBase64: true,
});

export default InlineEmoji;
