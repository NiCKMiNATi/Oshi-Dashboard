"use client";

import { useCallback } from "react";
import { api } from "@/lib/api";
import {
  formatDate,
  formatTimestamp,
  matchingKeywords,
  STATUS_LABELS,
  trackedOshi,
} from "@/lib/display";
import { useApiResource } from "@/lib/use-api-resource";
import type { Oshi, Update, UpdateStatus } from "@/lib/types";
import { Modal } from "./modal";
import { CategoryBadge } from "./update-card";
import { StatusActions } from "./status-actions";
import { ErrorState } from "./feedback";

export function UpdateDrawer({
  id,
  revision,
  oshi,
  onClose,
  onChange,
  busy,
  error,
  retry,
}: {
  id: number;
  revision: number;
  oshi: Oshi[];
  onClose: () => void;
  onChange: (update: Update, status: UpdateStatus) => void;
  busy: boolean;
  error?: string;
  retry: () => void;
}) {
  const load = useCallback(
    (signal: AbortSignal) => api.getUpdate(id, signal),
    [id],
  );
  const resource = useApiResource(`detail-${id}-${revision}`, load);
  const update = resource.data;
  const keywords = update ? matchingKeywords(update, oshi) : [];
  return (
    <Modal titleId="drawer-heading" onClose={onClose} drawer>
      <div className="drawer-header">
        <h2 id="drawer-heading">Update details</h2>
        <button
          className="close-button"
          aria-label="Close update details"
          onClick={onClose}
        >
          ×
        </button>
      </div>
      {resource.loading && !update && (
        <p className="drawer-loading" role="status">
          Loading update details…
        </p>
      )}
      {Boolean(resource.error) && (
        <ErrorState compact error={resource.error} retry={retry} />
      )}
      {update && !resource.error && (
        <div className="drawer-body" aria-busy={resource.loading}>
          <div className="drawer-badges">
            <CategoryBadge category={update.category} />
            <span className="status-label">{STATUS_LABELS[update.status]}</span>
          </div>
          <h3 className="drawer-title">{update.title}</h3>
          <div className="drawer-priority">
            <span>Relevance score</span>
            <strong>
              {update.relevance_score}
              <small>/ 100</small>
            </strong>
          </div>
          <p className="drawer-summary">
            {update.summary || "No summary provided."}
          </p>
          <dl className="detail-metadata">
            <div>
              <dt>Source</dt>
              <dd>{update.source}</dd>
            </div>
            <div>
              <dt>Published</dt>
              <dd>
                {update.published_at ? (
                  <time dateTime={update.published_at}>
                    {formatTimestamp(update.published_at)}
                  </time>
                ) : (
                  "Not provided"
                )}
              </dd>
            </div>
            {update.start_date && (
              <div>
                <dt>Starts</dt>
                <dd>
                  <time dateTime={update.start_date}>
                    {formatDate(update.start_date, true)}
                  </time>
                </dd>
              </div>
            )}
            {update.end_date && (
              <div>
                <dt>Ends</dt>
                <dd>
                  <time dateTime={update.end_date}>
                    {formatDate(update.end_date, true)}
                  </time>
                </dd>
              </div>
            )}
            {update.deadline && (
              <div className="deadline-row">
                <dt>Deadline</dt>
                <dd>
                  <time dateTime={update.deadline}>
                    {formatTimestamp(update.deadline)}
                  </time>
                </dd>
              </div>
            )}
            {update.location && (
              <div>
                <dt>Location</dt>
                <dd>{update.location}</dd>
              </div>
            )}
          </dl>
          <section className="drawer-context">
            <h4 className="eyebrow">Tracked oshi</h4>
            <div className="badge-list">
              {trackedOshi(update, oshi).map((item) => (
                <span className="badge" key={item.id}>
                  {item.name}
                  {!item.active ? " · Paused" : ""}
                </span>
              ))}
              {!trackedOshi(update, oshi).length && <p>No linked oshi.</p>}
            </div>
          </section>
          <section className="drawer-context">
            <h4 className="eyebrow">Keyword matches in this text</h4>
            <div className="badge-list">
              {keywords.map((keyword) => (
                <span className="badge" key={keyword}>
                  {keyword}
                </span>
              ))}
            </div>
            <p className="help-text">
              {keywords.length
                ? "Found in the title or summary among your active, weighted keywords."
                : "No active, weighted keywords match the title or summary."}
            </p>
          </section>
          <a
            className="button button-primary source-link"
            href={update.source_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open source <span aria-hidden="true">↗</span>
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
          {error && (
            <p className="inline-error" role="alert">
              {error}
            </p>
          )}
          <div className="drawer-actions">
            <StatusActions
              update={update}
              drawer
              busy={busy || resource.loading}
              onChange={(status) => onChange(update, status)}
            />
          </div>
        </div>
      )}
    </Modal>
  );
}
