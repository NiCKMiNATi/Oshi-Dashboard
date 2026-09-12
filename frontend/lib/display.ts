import type { Category, Oshi, Update, UpdateStatus } from "./types";

export const CATEGORY_LABELS: Record<Category, string> = {
  NEWS: "News",
  EVENT: "Events",
  MERCH: "Merch",
  COLLAB: "Collabs",
  MOVIE: "Movies",
  RELEASE: "Releases",
  OTHER: "Other",
};
export const STATUS_LABELS: Record<UpdateStatus, string> = {
  NEW: "New",
  SAVED: "Saved",
  INTERESTED: "Interested",
  GOING: "Going",
  BOUGHT: "Bought",
  IGNORED: "Ignored",
};

export function normalize(value: string): string {
  return value.normalize("NFKC").toLocaleLowerCase("en-US").trim();
}

export function trackedOshi(update: Update, oshi: Oshi[]): Oshi[] {
  return oshi.filter((item) => update.oshi_ids.includes(item.id));
}

export function matchingKeywords(update: Update, oshi: Oshi[]): string[] {
  const text = normalize(`${update.title}\n${update.summary}`);
  return [
    ...new Set(
      trackedOshi(update, oshi)
        .filter((item) => item.active)
        .flatMap((item) =>
          item.keywords
            .filter(
              (keyword) =>
                keyword.weight > 0 && text.includes(normalize(keyword.value)),
            )
            .map((keyword) => keyword.value),
        ),
    ),
  ];
}

export function matchesSearch(
  update: Update,
  oshi: Oshi[],
  search: string,
): boolean {
  const haystack = normalize(
    [
      update.title,
      update.summary,
      update.source,
      ...trackedOshi(update, oshi).map((item) => item.name),
    ].join(" "),
  );
  return haystack.includes(normalize(search));
}

export function formatDate(value: string | null, full = false): string {
  if (!value) return "Not provided";
  const calendarDate = /^\d{4}-\d{2}-\d{2}$/.test(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    ...(full ? { year: "numeric" } : {}),
    ...(calendarDate ? { timeZone: "UTC" } : {}),
  }).format(new Date(calendarDate ? `${value}T00:00:00Z` : value));
}

export function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(value));
}

export function oshiMarker(oshi: Oshi): string {
  if (oshi.type === "GAME") return "/oshi/teal.svg";
  if (oshi.type === "IDOL" || oshi.type === "ARTIST" || oshi.type === "SEIYUU")
    return "/oshi/pink.svg";
  return "/oshi/blue.svg";
}
