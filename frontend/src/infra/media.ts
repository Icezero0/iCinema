import { MEDIA_ORIGIN } from "@/infra/runtime-config";

export function resolveMediaUrl(path?: string | null) {
  if (!path) return "";

  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  if (path.startsWith("//")) {
    const protocol = window.location.protocol === "icinema:"
      ? new URL(MEDIA_ORIGIN).protocol
      : window.location.protocol;
    return `${protocol}${path}`;
  }

  if (path.startsWith("/")) {
    return `${MEDIA_ORIGIN}${path}`;
  }

  return `${MEDIA_ORIGIN}/${path}`;
}
