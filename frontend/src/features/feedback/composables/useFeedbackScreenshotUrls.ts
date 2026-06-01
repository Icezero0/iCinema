import { onBeforeUnmount, ref } from "vue";

export function useFeedbackScreenshotUrls(
  loadBlob: (assetId: number) => Promise<Blob>,
) {
  const urls = ref<Record<number, string>>({});
  const loadingIds = ref<number[]>([]);
  const failedIds = ref<number[]>([]);

  function isLoading(assetId: number) {
    return loadingIds.value.includes(assetId);
  }

  function hasFailed(assetId: number) {
    return failedIds.value.includes(assetId);
  }

  function markLoading(assetId: number) {
    if (!loadingIds.value.includes(assetId)) {
      loadingIds.value = [...loadingIds.value, assetId];
    }
  }

  function clearLoading(assetId: number) {
    loadingIds.value = loadingIds.value.filter((id) => id !== assetId);
  }

  function clearFailed(assetId: number) {
    failedIds.value = failedIds.value.filter((id) => id !== assetId);
  }

  function markFailed(assetId: number) {
    if (!failedIds.value.includes(assetId)) {
      failedIds.value = [...failedIds.value, assetId];
    }
  }

  function setUrl(assetId: number, url: string) {
    urls.value = {
      ...urls.value,
      [assetId]: url,
    };
  }

  async function ensureUrl(assetId: number) {
    const cached = urls.value[assetId];
    if (cached) return cached;
    if (isLoading(assetId)) return "";

    markLoading(assetId);
    clearFailed(assetId);

    try {
      const blob = await loadBlob(assetId);
      const objectUrl = URL.createObjectURL(blob);
      setUrl(assetId, objectUrl);
      return objectUrl;
    } catch (err) {
      markFailed(assetId);
      throw err;
    } finally {
      clearLoading(assetId);
    }
  }

  async function loadAll(assetIds: number[]) {
    const results = await Promise.allSettled(assetIds.map((assetId) => ensureUrl(assetId)));
    return results.filter((result) => result.status === "rejected").length;
  }

  function revokeAll() {
    Object.values(urls.value).forEach((url) => URL.revokeObjectURL(url));
    urls.value = {};
    loadingIds.value = [];
    failedIds.value = [];
  }

  onBeforeUnmount(revokeAll);

  return {
    urls,
    loadingIds,
    failedIds,
    isLoading,
    hasFailed,
    ensureUrl,
    loadAll,
    revokeAll,
  };
}
