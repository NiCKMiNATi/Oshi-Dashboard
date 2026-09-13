import type {
  CatalogCandidate,
  FeedFilters,
  Oshi,
  OshiInput,
  Stats,
  Update,
  UpdateStatus,
} from "./types";

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly unavailable = false,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function errorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item)
          return String(item.msg);
        return "Please check the submitted values.";
      })
      .join(" ");
  }
  if (detail && typeof detail === "object" && "message" in detail)
    return String(detail.message);
  return "The request could not be completed. Please try again.";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const timeout = AbortSignal.timeout(10_000);
  const signal = options.signal
    ? AbortSignal.any([options.signal, timeout])
    : timeout;
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      signal,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError(
      "The local API is unavailable. Start the backend and try again.",
      true,
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(errorDetail(body.detail), false, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  discover: (q: string, signal?: AbortSignal) =>
    request<CatalogCandidate[]>(`/api/discover?${new URLSearchParams({ q })}`, {
      signal,
    }),
  trackEntity: (id: number) =>
    request<Oshi>(`/api/discover/${id}/track`, { method: "POST" }),
  getOshi: (signal?: AbortSignal) => request<Oshi[]>("/api/oshi", { signal }),
  getStats: (signal?: AbortSignal) => request<Stats>("/api/stats", { signal }),
  getUpdates: (
    filters: FeedFilters,
    signal?: AbortSignal,
    limit = 50,
    offset = 0,
  ) => {
    const query = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined) query.set(key, String(value));
    });
    return request<Update[]>(`/api/updates?${query}`, { signal });
  },
  getUpdate: (id: number, signal?: AbortSignal) =>
    request<Update>(`/api/updates/${id}`, { signal }),
  setStatus: (id: number, status: UpdateStatus) =>
    request<Update>(`/api/updates/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  createOshi: (input: OshiInput) =>
    request<Oshi>("/api/oshi", { method: "POST", body: JSON.stringify(input) }),
  updateOshi: (id: number, input: Partial<OshiInput>) =>
    request<Oshi>(`/api/oshi/${id}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    }),
  deleteOshi: (id: number) =>
    request<void>(`/api/oshi/${id}`, { method: "DELETE" }),
};

export function describeError(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}
