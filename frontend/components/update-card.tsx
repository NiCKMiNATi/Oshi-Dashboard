"use client";

import { formatDate, formatTimestamp, trackedOshi } from "@/lib/display";
import type { Oshi, Update, UpdateStatus } from "@/lib/types";
import { StatusActions } from "./status-actions";

export function CategoryBadge({ category }: { category: Update["category"] }) {
  return (
    <span className={`badge category-badge category-${category.toLowerCase()}`}>
      {category}
    </span>
  );
}

export function UpdateCard({
  update,
  oshi,
  open,
  changeStatus,
  busy,
}: {
  update: Update;
  oshi: Oshi[];
  open: () => void;
  changeStatus: (status: UpdateStatus) => void;
  busy: boolean;
}) {
  // Show one action date. Full event ranges belong in the drawer.
  const starts =
    !update.deadline &&
    ["EVENT", "COLLAB", "MOVIE", "RELEASE"].includes(update.category)
      ? update.start_date
      : null;
  const hasActionable = Boolean(update.deadline || starts || update.location);
  const priority =
    update.relevance_score >= 80
      ? "high"
      : update.relevance_score >= 50
        ? "medium"
        : "low";
  return (
    <article
      className={`update-card ${hasActionable ? "has-actionable" : ""} ${update.status === "IGNORED" ? "ignored-card" : ""}`}
      data-update-id={update.id}
    >
      <div className="card-badges">
        <CategoryBadge category={update.category} />
        {trackedOshi(update, oshi).map((item) => (
          <span className="badge oshi-badge" key={item.id}>
            {item.name}
          </span>
        ))}
      </div>
      <h2>
        <button className="card-open" onClick={open} aria-haspopup="dialog">
          {update.title}
        </button>
      </h2>
      {hasActionable && (
        <dl className="card-actionable" aria-label="Dates and location">
          {update.deadline && (
            <div className="card-deadline">
              <dt>締切</dt>
              <dd>
                <time
                  dateTime={update.deadline}
                  title={formatTimestamp(update.deadline)}
                  aria-label={formatTimestamp(update.deadline)}
                >
                  {formatDate(
                    update.deadline,
                    new Date(update.deadline).getFullYear() !==
                      new Date().getFullYear(),
                  )}
                  {" · "}
                  {new Intl.DateTimeFormat("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                    hourCycle: "h23",
                  }).format(new Date(update.deadline))}
                </time>
              </dd>
            </div>
          )}
          {starts && (
            <div className="card-start">
              <dt>Starts</dt>
              <dd>
                <time dateTime={starts}>{formatDate(starts, true)}</time>
              </dd>
            </div>
          )}
          {update.location && (
            <div className="card-location">
              <dt className="sr-only">Location</dt>
              <dd>{update.location}</dd>
            </div>
          )}
        </dl>
      )}
      {update.summary && <p className="card-summary">{update.summary}</p>}
      <div className="card-footer">
        <StatusActions update={update} onChange={changeStatus} busy={busy} />
      </div>
      <span
        className={`priority-score priority-${priority}`}
        title={`Relevance ${update.relevance_score} out of 100`}
      >
        <span className="sr-only">Relevance </span>
        {priority.toUpperCase()} <strong>{update.relevance_score}</strong>
        <span className="sr-only"> out of 100</span>
      </span>
    </article>
  );
}
