import type { Ref } from "vue";
import { useI18n } from "vue-i18n";
import { useMediaViewerStore } from "@/stores/media-viewer.store";
import { useStickersStore } from "@/stores/stickers.store";
import { useToastsStore } from "@/stores/toasts.store";

type ChatMediaKind = "emoji" | "image" | "sticker";

type UseChatMediaActionsOptions = {
  kind: Ref<ChatMediaKind>;
  src: Ref<string | undefined>;
  alt: Ref<string>;
  assetId: Ref<string | null | undefined>;
  closeContextMenu: () => void;
  selectMessageNode: () => void;
};

export function useChatMediaActions(options: UseChatMediaActionsOptions) {
  const {
    kind,
    src,
    alt,
    assetId,
    closeContextMenu,
    selectMessageNode,
  } = options;

  const { t } = useI18n();
  const mediaViewer = useMediaViewerStore();
  const stickersStore = useStickersStore();
  const toasts = useToastsStore();

  function openMediaViewer() {
    if (
      !src.value ||
      (kind.value !== "image" && kind.value !== "sticker")
    ) {
      return;
    }

    mediaViewer.openViewer({
      src: src.value,
      alt: alt.value,
    });
  }

  function getDownloadFilename() {
    const fallbackBase = kind.value === "sticker"
      ? `sticker-${assetId.value || "media"}`
      : `image-${assetId.value || "media"}`;

    if (!src.value) {
      return `${fallbackBase}.png`;
    }

    try {
      const url = new URL(src.value, window.location.href);
      const pathname = url.pathname;
      const extension = pathname.match(/\.([a-zA-Z0-9]+)$/)?.[1] ?? "png";
      return `${fallbackBase}.${extension}`;
    } catch {
      return `${fallbackBase}.png`;
    }
  }

  function getDownloadUrl() {
    if (!src.value) return "";

    try {
      const url = new URL(src.value, window.location.href);
      const isCrossOrigin = url.origin !== window.location.origin;
      const isPublicMediaPath = /^\/(avatar|image|sticker)\//.test(url.pathname);

      if (isCrossOrigin && isPublicMediaPath) {
        return `${window.location.origin}${url.pathname}${url.search}`;
      }

      return url.toString();
    } catch {
      return src.value;
    }
  }

  function parsePositiveAssetId() {
    const parsed = Number(assetId.value);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }

  async function copyMedia() {
    selectMessageNode();

    try {
      const copied = document.execCommand("copy");
      if (!copied) {
        throw new Error("copy-failed");
      }
    } catch {
      toasts.push({
        message: t("chat.mediaMenu.copyFailed"),
        tone: "danger",
      });
    } finally {
      closeContextMenu();
    }
  }

  async function saveMedia() {
    if (!src.value) return;

    try {
      const response = await fetch(getDownloadUrl());
      if (!response.ok) {
        throw new Error(`save-failed:${response.status}`);
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = getDownloadFilename();
      link.rel = "noopener";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(() => {
        URL.revokeObjectURL(objectUrl);
      }, 1000);
    } catch {
      toasts.push({
        message: t("chat.mediaMenu.saveFailed"),
        tone: "danger",
      });
    } finally {
      closeContextMenu();
    }
  }

  async function collectMedia() {
    if (stickersStore.isEditingLibrary) {
      toasts.push({
        message: t("chat.mediaMenu.collectBlockedDuringStickerEdit"),
        tone: "warning",
      });
      closeContextMenu();
      return;
    }

    if ((kind.value !== "sticker" && kind.value !== "image") || !assetId.value) {
      toasts.push({
        message: t("chat.mediaMenu.collectImageUnsupported"),
        tone: "warning",
      });
      closeContextMenu();
      return;
    }

    const mediaId = parsePositiveAssetId();
    if (!mediaId) {
      toasts.push({
        message: t("chat.mediaMenu.collectImageUnsupported"),
        tone: "warning",
      });
      closeContextMenu();
      return;
    }

    if (kind.value === "sticker" && stickersStore.libraryIds.includes(mediaId)) {
      toasts.push({
        message: t("chat.emojiPanel.stickerUpload.duplicate"),
        tone: "warning",
      });
      closeContextMenu();
      return;
    }

    try {
      if (kind.value === "image") {
        const result = await stickersStore.collectImageAsSticker(mediaId);
        toasts.push({
          message: result.existedInLibrary
            ? t("chat.emojiPanel.stickerUpload.duplicate")
            : t("chat.mediaMenu.collectSuccess"),
          tone: result.existedInLibrary ? "warning" : "success",
        });
      } else {
        await stickersStore.collectSticker(mediaId);
        toasts.push({
          message: t("chat.mediaMenu.collectSuccess"),
          tone: "success",
        });
      }
    } catch {
      toasts.push({
        message: stickersStore.error || t("chat.mediaMenu.collectFailed"),
        tone: "danger",
      });
    } finally {
      closeContextMenu();
    }
  }

  function viewMedia() {
    openMediaViewer();
    closeContextMenu();
  }

  return {
    openMediaViewer,
    copyMedia,
    saveMedia,
    collectMedia,
    viewMedia,
  };
}
