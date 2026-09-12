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
    drawer ? ["GOING", "Going"] : ["INTERESTED", "Interested"],
    ["IGNORED", "Ignore"],
  ];
  return (
    <div className="status-actions" aria-label="Update actions">
      {actions.map(([status, label]) => (
        <button
          key={status}
          className={`button button-small ${update.status === status ? "is-active" : ""} ${status === "IGNORED" ? "ignore-action" : ""}`}
          disabled={busy}
          aria-pressed={update.status === status}
          onClick={() => onChange(status)}
        >
          {update.status === status ? STATUS_LABELS[status] : label}
        </button>
      ))}
      {busy && (
        <span className="action-progress" role="status">
          Saving…
        </span>
      )}
    </div>
  );
}
