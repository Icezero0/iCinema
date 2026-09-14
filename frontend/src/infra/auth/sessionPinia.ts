import type { PiniaPluginContext } from "pinia";
import { onSessionReset } from "./session";

export function resetStoresOnSessionChange({ store }: PiniaPluginContext) {
  if (store.$id === "auth" || store.$id === "toasts") return;
  const stop = onSessionReset(() => store.$reset());
  const dispose = store.$dispose.bind(store);
  store.$dispose = () => { stop(); dispose(); };
}
