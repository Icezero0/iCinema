function normalizeDateInput(value: string) {
  return /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`;
}

export function parseApiDate(value?: string | null) {
  if (!value) return null;

  const date = new Date(normalizeDateInput(value));
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatLocalDateTime(value?: string | null) {
  if (!value) return "-";

  const date = parseApiDate(value);
  if (!date) return value;

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
