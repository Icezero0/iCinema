const API_ORIGIN = import.meta.env.VITE_API_ORIGIN ?? window.location.origin ?? "http://localhost:8000";

export function resolveMediaUrl(path?: string | null) {
  if (!path) return "";

  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  if (path.startsWith("//")) {
    return `${window.location.protocol}${path}`;
  }

  if (path.startsWith("/")) {
    return `${API_ORIGIN}${path}`;
  }

  return `${API_ORIGIN}/${path}`;
}
