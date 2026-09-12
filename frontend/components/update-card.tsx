"use client";

import {
  formatDate,
  matchingKeywords,
  STATUS_LABELS,
  trackedOshi,
} from "@/lib/display";
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
  const keywords = matchingKeywords(update, oshi);
  return (
    <article
      className={`update-card ${update.status === "IGNORED" ? "ignored-card" : ""}`}
      data-update-id={update.id}
    >
      <div className="card-badges">
        <CategoryBadge category={update.category} />
        {trackedOshi(update, oshi).map((item) => (
          <span className="badge oshi-badge" key={item.id}>
            {item.name}
          </span>
        ))}
        <span className="priority-score" title="Relevance score out of 100">
          Priority <strong>{update.relevance_score}</strong>
        </span>
      </div>
      <h2>
        <button className="card-open" onClick={open} aria-haspopup="dialog">
          {update.title}
        </button>
      </h2>
      <p className="card-summary">{update.summary || "No summary provided."}</p>
      <div className="card-metadata">
        <span>{update.source}</span>
        <span aria-hidden="true">·</span>
        {update.published_at ? (
          <time dateTime={update.published_at}>
            {formatDate(update.published_at)}
          </time>
        ) : (
          <span>Unpublished date</span>
        )}
        {keywords.length > 0 && (
          <>
            <span aria-hidden="true">·</span>
            <span className="card-keywords">
              {keywords.slice(0, 3).join(" / ")}
            </span>
          </>
        )}
      </div>
      <div className="card-footer">
        <StatusActions update={update} onChange={changeStatus} busy={busy} />
        <span className={`status-label status-${update.status.toLowerCase()}`}>
          {STATUS_LABELS[update.status]}
        </span>
      </div>
    </article>
  );
}
