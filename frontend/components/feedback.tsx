"use client";

import { ApiError, describeError } from "@/lib/api";

export function ErrorState({
  error,
  retry,
  compact = false,
}: {
  error: unknown;
  retry: () => void;
  compact?: boolean;
}) {
  const unavailable = error instanceof ApiError && error.unavailable;
  return (
    <div className={`error-state ${compact ? "compact" : ""}`} role="alert">
      <span className="error-symbol" aria-hidden="true">
        !
      </span>
      <div>
        <h2>
          {unavailable
            ? "Your local backend is offline"
            : "We couldn’t load this"}
        </h2>
        <p>{describeError(error)}</p>
        {unavailable && (
          <p className="help-text">
            Your saved data is safe. Start the backend, then retry.
          </p>
        )}
      </div>
      <button className="button" onClick={retry}>
        Try again
      </button>
    </div>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-mark" aria-hidden="true">
        ○
      </span>
      <h2>{title}</h2>
      <p>{children}</p>
      {action}
    </div>
  );
}

export function FeedSkeleton() {
  return (
    <div className="feed-skeleton" role="status" aria-label="Loading updates">
      {[0, 1, 2].map((n) => (
        <div className="skeleton-card" key={n}>
          <span />
          <span />
          <span />
          <span />
        </div>
      ))}
      <span className="sr-only">Loading updates…</span>
    </div>
  );
}
