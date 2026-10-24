function downloadUrl(value: string | undefined) {
  try {
    const url = new URL(value || "");
    return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password
      ? url.href : "";
  } catch {
    return "";
  }
}

export const desktopDownloadUrl = downloadUrl(import.meta.env.VITE_DESKTOP_DOWNLOAD_URL);
export const windowsPortableDownloadUrl = downloadUrl(import.meta.env.VITE_DESKTOP_PORTABLE_DOWNLOAD_URL)
  || desktopDownloadUrl;
export const windowsInstallerDownloadUrl = downloadUrl(import.meta.env.VITE_DESKTOP_INSTALLER_DOWNLOAD_URL);
