export type DesktopInfo = Readonly<{
  version: string;
  storagePath: string;
  mode: "development" | "portable" | "installed";
  platform: string;
  arch: string;
}>;

export type DesktopUpdate = Readonly<{
  status: "available" | "current" | "unpublished";
  latestVersion: string | null;
  releaseUrl: string;
  checkedAt: string;
}>;

declare global {
  interface Window {
    icinemaDesktop?: Readonly<{
      getInfo: () => Promise<DesktopInfo>;
      checkForUpdates: () => Promise<DesktopUpdate>;
      openDataFolder: () => Promise<void>;
    }>;
  }
}

export const desktop = window.icinemaDesktop;
