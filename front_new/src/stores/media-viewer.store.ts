import { defineStore } from "pinia";

type ViewerPayload = {
  src: string;
  alt?: string;
};

type State = {
  open: boolean;
  src: string;
  alt: string;
  scale: number;
};

function clampScale(value: number) {
  return Math.min(4, Math.max(0.25, value));
}

export const useMediaViewerStore = defineStore("mediaViewer", {
  state: (): State => ({
    open: false,
    src: "",
    alt: "",
    scale: 1,
  }),

  actions: {
    openViewer(payload: ViewerPayload) {
      this.open = true;
      this.src = payload.src;
      this.alt = payload.alt ?? "";
      this.scale = 1;
    },

    closeViewer() {
      this.open = false;
      this.src = "";
      this.alt = "";
      this.scale = 1;
    },

    setScale(scale: number) {
      this.scale = clampScale(scale);
    },

    zoomBy(delta: number) {
      this.scale = clampScale(this.scale + delta);
    },
  },
});
