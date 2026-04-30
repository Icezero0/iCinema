import { computed, nextTick, ref } from "vue";
import type { PocLogEntry } from "./types";

export function usePocLogger(collectMetrics: () => Record<string, unknown>) {
  const logs = ref<PocLogEntry[]>([]);

  const logText = computed(() =>
    logs.value
      .map((entry) => JSON.stringify(entry, null, 2))
      .join("\n\n"));

  function writeLog(event: string, data: Record<string, unknown> = {}) {
    if (event !== "stateTransition") return;

    const entry = {
      at: new Date().toISOString(),
      event,
      data: {
        ...data,
        metrics: collectMetrics(),
      },
    };

    logs.value.push(entry);
    console.info("[iCinema HLS POC]", entry);
  }

  function clearLogs() {
    logs.value = [];
  }

  async function copyLogs() {
    await navigator.clipboard?.writeText(logText.value);
    writeLog("logsCopied");
    await nextTick();
  }

  return {
    logText,
    writeLog,
    clearLogs,
    copyLogs,
  };
}
