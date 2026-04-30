import { defineStore } from "pinia";

export type ToastTone = "default" | "success" | "warning" | "danger";

export type ToastItem = {
  id: number;
  message: string;
  tone: ToastTone;
  durationMs: number;
};

type State = {
  items: ToastItem[];
  nextId: number;
};

const DEFAULT_DURATION_MS = 2600;

export const useToastsStore = defineStore("toasts", {
  state: (): State => ({
    items: [],
    nextId: 1,
  }),

  actions: {
    push(input: {
      message: string;
      tone?: ToastTone;
      durationMs?: number;
    }) {
      const toast: ToastItem = {
        id: this.nextId,
        message: input.message,
        tone: input.tone ?? "default",
        durationMs: input.durationMs ?? DEFAULT_DURATION_MS,
      };

      this.nextId += 1;
      this.items = [...this.items, toast];

      window.setTimeout(() => {
        this.dismiss(toast.id);
      }, toast.durationMs);

      return toast.id;
    },

    dismiss(toastId: number) {
      this.items = this.items.filter((item) => item.id !== toastId);
    },

    clear() {
      this.items = [];
    },
  },
});
