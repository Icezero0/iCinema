import { onBeforeUnmount, ref } from "vue";

export type LocalImagePreview = {
  id: number;
  file: File;
  url: string;
};

type AddFilesResult = {
  added: number;
  rejected: number;
};

export function useLocalImagePreviews(options: { maxCount: number }) {
  const previews = ref<LocalImagePreview[]>([]);
  let nextPreviewId = 1;

  function addFiles(files: File[]): AddFilesResult {
    const availableCount = Math.max(0, options.maxCount - previews.value.length);
    const acceptedFiles = files.slice(0, availableCount);

    for (const file of acceptedFiles) {
      previews.value.push({
        id: nextPreviewId,
        file,
        url: URL.createObjectURL(file),
      });
      nextPreviewId += 1;
    }

    return {
      added: acceptedFiles.length,
      rejected: files.length - acceptedFiles.length,
    };
  }

  function removePreview(id: number) {
    const target = previews.value.find((item) => item.id === id);
    if (target) {
      URL.revokeObjectURL(target.url);
    }
    previews.value = previews.value.filter((item) => item.id !== id);
  }

  function clearPreviews() {
    for (const item of previews.value) {
      URL.revokeObjectURL(item.url);
    }
    previews.value = [];
  }

  onBeforeUnmount(clearPreviews);

  return {
    previews,
    addFiles,
    removePreview,
    clearPreviews,
  };
}
