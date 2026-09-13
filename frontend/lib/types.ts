export const OSHI_TYPES = [
  "ANIME",
  "CHARACTER",
  "GAME",
  "IDOL",
  "SEIYUU",
  "ARTIST",
  "MANGA",
  "OTHER",
] as const;
export const CATEGORIES = [
  "NEWS",
  "EVENT",
  "MERCH",
  "COLLAB",
  "MOVIE",
  "RELEASE",
  "OTHER",
] as const;
export const STATUSES = [
  "NEW",
  "SAVED",
  "INTERESTED",
  "GOING",
  "BOUGHT",
  "IGNORED",
] as const;

export type OshiType = (typeof OSHI_TYPES)[number];
export type Category = (typeof CATEGORIES)[number];
export type UpdateStatus = (typeof STATUSES)[number];

export interface KeywordInput {
  value: string;
  weight: number;
}
export interface Keyword extends KeywordInput {
  id: number;
  oshi_id: number;
}
export interface OshiInput {
  name: string;
  type: OshiType;
  priority: number;
  active: boolean;
  keywords: KeywordInput[];
}
export interface Oshi extends Omit<OshiInput, "keywords"> {
  id: number;
  created_at: string;
  keywords: Keyword[];
}
export interface CatalogCandidate {
  id: number;
  name: string;
  type: OshiType;
  description: string | null;
  aliases: string[];
  provider: string;
  is_tracked: boolean;
}
export interface Update {
  id: number;
  title: string;
  summary: string;
  category: Category;
  source: string;
  source_url: string;
  published_at: string | null;
  start_date: string | null;
  end_date: string | null;
  deadline: string | null;
  location: string | null;
  relevance_score: number;
  status: UpdateStatus;
  created_at: string;
  oshi_ids: number[];
}
export interface Stats {
  total_oshi: number;
  active_oshi: number;
  total_updates: number;
  by_category: Record<Category, number>;
  by_status: Record<UpdateStatus, number>;
}
export interface FeedFilters {
  oshi?: number;
  category?: Category;
  status?: UpdateStatus;
  min_score?: number;
}
