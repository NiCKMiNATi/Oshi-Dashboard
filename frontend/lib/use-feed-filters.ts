"use client";

import { useRouter, useSearchParams } from "next/navigation";
import {
  CATEGORIES,
  STATUSES,
  type Category,
  type FeedFilters,
  type UpdateStatus,
} from "./types";

export function feedHref(filters: FeedFilters): string {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined) query.set(key, String(value));
  });
  return query.size ? `/?${query}` : "/";
}

export function useFeedFilters() {
  const params = useSearchParams();
  const router = useRouter();
  const oshiValue = params.get("oshi");
  const scoreValue = params.get("min_score");
  const category = params.get("category") as Category;
  const status = params.get("status") as UpdateStatus;
  const filters: FeedFilters = {
    oshi:
      oshiValue && /^\d+$/.test(oshiValue) && Number(oshiValue) > 0
        ? Number(oshiValue)
        : undefined,
    category: CATEGORIES.includes(category) ? category : undefined,
    status: STATUSES.includes(status) ? status : undefined,
    min_score:
      scoreValue && /^\d+$/.test(scoreValue) && Number(scoreValue) <= 100
        ? Number(scoreValue)
        : undefined,
  };
  return {
    filters,
    setFilters: (changes: Partial<FeedFilters>) =>
      router.replace(feedHref({ ...filters, ...changes }), { scroll: false }),
  };
}
