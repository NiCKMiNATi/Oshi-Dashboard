"use client";

import type { Update, UpdateStatus } from "@/lib/types";
import { STATUS_LABELS } from "@/lib/display";

export function StatusActions({
  update,
  onChange,
  busy,
  drawer = false,
}: {
  update: Update;
  onChange: (status: UpdateStatus) => void;
  busy: boolean;
  drawer?: boolean;
}) {
  const actions: [UpdateStatus, string][] = [
    ["SAVED", "Save"],
    ["INTERESTED", "Interested"],
    ...(drawer ? [["GOING", "Going"] as [UpdateStatus, string]] : []),
    ["IGNORED", "Ignore"],
  ];
  return (
    <div className="status-actions" role="group" aria-label="Update actions">
      {actions.map(([status, label]) => (
        <button
          key={status}
          className={`button button-small ${update.status === status ? "is-active" : ""} ${status === "IGNORED" ? "ignore-action" : ""}`}
          disabled={busy}
          aria-pressed={update.status === status}
          onClick={() => onChange(status)}
        >
          {update.status === status ? (
            <span className={`status-label status-${status.toLowerCase()}`}>
              {STATUS_LABELS[status]}
            </span>
          ) : (
            label
          )}
        </button>
      ))}
      {!actions.some(([status]) => update.status === status) && (
        <span
          className={`current-status status-${update.status.toLowerCase()}`}
        >
          <span className="sr-only">Current status: </span>
          <span className="status-label">{STATUS_LABELS[update.status]}</span>
        </span>
      )}
      {busy && (
        <span className="action-progress" role="status">
          Saving…
        </span>
      )}
    </div>
  );
}
