import { defineStore } from "pinia";

type ViewerPayload = {
  src: string;
  alt?: string;
  revokeOnClose?: boolean;
};

type State = {
  open: boolean;
  src: string;
  alt: string;
  scale: number;
  managedObjectUrl: string;
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
    managedObjectUrl: "",
  }),

  actions: {
    revokeManagedObjectUrl() {
      if (!this.managedObjectUrl) return;
      URL.revokeObjectURL(this.managedObjectUrl);
      this.managedObjectUrl = "";
    },

    openViewer(payload: ViewerPayload) {
      this.revokeManagedObjectUrl();
      this.open = true;
      this.src = payload.src;
      this.alt = payload.alt ?? "";
      this.scale = 1;
      this.managedObjectUrl = payload.revokeOnClose ? payload.src : "";
    },

    closeViewer() {
      this.open = false;
      this.src = "";
      this.alt = "";
      this.scale = 1;
      this.revokeManagedObjectUrl();
    },

    setScale(scale: number) {
      this.scale = clampScale(scale);
    },

    zoomBy(delta: number) {
      this.scale = clampScale(this.scale + delta);
    },
  },
});
