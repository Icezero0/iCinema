declare global {
  interface Window {
    icinemaDesktopConfig?: Readonly<{
      apiOrigin: string;
      wsOrigin: string;
      storageMode: "development" | "portable" | "installed";
      storagePath: string;
    }>;
  }
}

export const desktopConfig = window.icinemaDesktopConfig;
export const API_ORIGIN = desktopConfig?.apiOrigin ?? import.meta.env.VITE_API_ORIGIN ?? "http://localhost:8000";
export const MEDIA_ORIGIN = desktopConfig?.apiOrigin ?? import.meta.env.VITE_API_ORIGIN ?? window.location.origin;
