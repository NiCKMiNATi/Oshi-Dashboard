"use client";

import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import {
  formatDate,
  formatTimestamp,
  isDemoUpdate,
  matchingKeywords,
  sourceHref,
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
  const [closing, setClosing] = useState(false);
  const requestClose = () => setClosing(true);
  const load = useCallback(
    (signal: AbortSignal) => api.getUpdate(id, signal),
    [id],
  );
  const resource = useApiResource(`detail-${id}-${revision}`, load);
  const update = resource.data;
  const keywords = update ? matchingKeywords(update, oshi) : [];
  const linked = update ? trackedOshi(update, oshi) : [];
  const demo = update ? isDemoUpdate(update) : false;
  const href = update ? sourceHref(update.source_url) : undefined;
  return (
    <Modal
      titleId="drawer-heading"
      onClose={requestClose}
      drawer
      closing={closing}
      onExitComplete={onClose}
    >
      <div className="drawer-header">
        <h2 id="drawer-heading">Update details</h2>
        <button
          className="close-button"
          aria-label="Close update details"
          onClick={requestClose}
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
          <section className="drawer-overview" aria-label="Overview">
            <div className="drawer-badges badge-list">
              <CategoryBadge category={update.category} />
              {linked.map((item) => (
                <span className="badge oshi-badge" key={item.id}>
                  {item.name}
                </span>
              ))}
            </div>
            <h3 className="drawer-title">{update.title}</h3>
            {update.summary && (
              <p className="drawer-summary">{update.summary}</p>
            )}
          </section>
          {(update.deadline ||
            update.start_date ||
            update.end_date ||
            update.location) && (
            <section
              className="drawer-section"
              aria-labelledby="action-heading"
            >
              <h4 id="action-heading">Action</h4>
              <dl className="detail-metadata">
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
                {update.location && (
                  <div>
                    <dt>Location</dt>
                    <dd>{update.location}</dd>
                  </div>
                )}
              </dl>
            </section>
          )}
          <section className="drawer-section" aria-labelledby="source-heading">
            <h4 id="source-heading">Source</h4>
            <p className="source-publisher">{update.source}</p>
            {update.published_at && (
              <p className="source-published">
                <time dateTime={update.published_at}>
                  {formatTimestamp(update.published_at)}
                </time>
              </p>
            )}
            {demo ? (
              <>
                <button className="button source-link" disabled>
                  Demo source
                </button>
                <p className="help-text">
                  Fictional sample — no external page.
                </p>
              </>
            ) : href ? (
              <a
                className="button source-link"
                href={href}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open source <span aria-hidden="true">↗</span>
                <span className="sr-only"> (opens in a new tab)</span>
              </a>
            ) : (
              <button className="button source-link" disabled>
                Source unavailable
              </button>
            )}
          </section>
          {(update.relevance_score > 0 ||
            keywords.length > 0 ||
            linked.length > 0) && (
            <details className="drawer-why">
              <summary>Why this appeared</summary>
              <p className="drawer-score">
                Relevance <strong>{update.relevance_score} / 100</strong>
              </p>
              {keywords.length > 0 && (
                <>
                  <p className="help-text">Keywords found in this update</p>
                  <div className="badge-list">
                    {keywords.map((keyword) => (
                      <span className="badge" key={keyword}>
                        {keyword}
                      </span>
                    ))}
                  </div>
                </>
              )}
            </details>
          )}
          {error && (
            <p className="inline-error" role="alert">
              {error}
            </p>
          )}
          <div className="drawer-actions">
            <StatusActions
              update={update}
              drawer
              busy={busy || resource.loading || closing}
              onChange={(status) => onChange(update, status)}
            />
          </div>
        </div>
      )}
    </Modal>
  );
}
