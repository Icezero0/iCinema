import Image from "@tiptap/extension-image";
import { VueNodeViewRenderer } from "@tiptap/vue-3";
import InlineMediaView from "./InlineMediaView.vue";

const InlineMedia = Image.extend({
  name: "inlineMedia",

  inline() {
    return true;
  },

  group() {
    return "inline";
  },

  parseHTML() {
    return [
      {
        tag: "img",
        getAttrs: (element) => {
          if (!(element instanceof HTMLElement)) return false;
          return element.getAttribute("data-kind") === "emoji" ? false : null;
        },
      },
    ];
  },

  addAttributes() {
    return {
      ...this.parent?.(),
      kind: {
        default: "image",
        parseHTML: (element: HTMLElement) => element.getAttribute("data-kind") || "image",
        renderHTML: (attributes: Record<string, unknown>) => ({
          "data-kind": String(attributes.kind || "image"),
        }),
      },
      assetId: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute("data-asset-id"),
        renderHTML: (attributes: Record<string, unknown>) => {
          if (!attributes.assetId) return {};
          return { "data-asset-id": String(attributes.assetId) };
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

export default InlineMedia;
