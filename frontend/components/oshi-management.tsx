"use client";

import Image from "next/image";
import { useState } from "react";
import { api, describeError } from "@/lib/api";
import { oshiMarker } from "@/lib/display";
import type { Oshi } from "@/lib/types";
import { useAppData } from "./app-shell";
import { EmptyState, ErrorState } from "./feedback";
import { Modal } from "./modal";

export function StatCard({
  label,
  value,
  detail,
}: {
  label: string;
  value?: number;
  detail: string;
}) {
  return (
    <div className="stat-card">
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
      <small>{detail}</small>
    </div>
  );
}

export function OshiTable({
  oshi,
  edit,
  remove,
  toggle,
  busyId,
}: {
  oshi: Oshi[];
  edit: (oshi: Oshi) => void;
  remove: (oshi: Oshi) => void;
  toggle: (oshi: Oshi) => void;
  busyId: number | null;
}) {
  return (
    <div className="table-scroll">
      <table className="oshi-table">
        <caption className="sr-only">
          Your tracked oshi, priorities, keywords, and active states
        </caption>
        <thead>
          <tr>
            <th scope="col">Oshi</th>
            <th scope="col">Type</th>
            <th scope="col">Priority</th>
            <th scope="col">Keywords</th>
            <th scope="col">Status</th>
            <th scope="col">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {oshi.map((item) => (
            <tr key={item.id} data-oshi-id={item.id}>
              <th scope="row">
                <span className="table-oshi-name">
                  <Image
                    src={oshiMarker(item)}
                    width={8}
                    height={8}
                    alt=""
                    unoptimized
                  />
                  {item.name}
                </span>
              </th>
              <td>
                <span className="type-label">{item.type}</span>
              </td>
              <td>
                <span className="priority-value">
                  {item.priority}
                  <span>/ 100</span>
                </span>
              </td>
              <td>
                <div className="table-keywords">
                  {item.keywords.length ? (
                    item.keywords.map((keyword) => (
                      <span
                        className={`badge ${keyword.weight === 0 ? "disabled-keyword" : ""}`}
                        title={`Weight: ${keyword.weight}`}
                        key={keyword.id}
                      >
                        {keyword.value}
                        <small>{keyword.weight}</small>
                      </span>
                    ))
                  ) : (
                    <span className="muted">No keywords</span>
                  )}
                </div>
              </td>
              <td>
                <button
                  className={`active-toggle ${item.active ? "active" : ""}`}
                  aria-label={`${item.active ? "Pause" : "Activate"} ${item.name}`}
                  aria-pressed={item.active}
                  disabled={busyId !== null}
                  onClick={() => toggle(item)}
                >
                  <span aria-hidden="true" />
                  {busyId === item.id
                    ? "Saving…"
                    : item.active
                      ? "Active"
                      : "Paused"}
                </button>
              </td>
              <td>
                <div className="table-actions">
                  <button
                    className="text-button"
                    onClick={() => edit(item)}
                    aria-label={`Edit ${item.name}`}
                    disabled={busyId !== null}
                  >
                    Edit
                  </button>
                  <button
                    className="text-button danger-text"
                    onClick={() => remove(item)}
                    aria-label={`Delete ${item.name}`}
                    disabled={busyId !== null}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const RULES = [
  ["Followed oshi", "+40", "At least one linked oshi is actively followed."],
  [
    "Priority keyword",
    "+25",
    "An active oshi’s keyword with weight > 0 matches the title or summary.",
  ],
  [
    "Japan event",
    "+20",
    "An EVENT has a supported Japan or city marker in its location.",
  ],
  [
    "Action deadline",
    "+20",
    "A deadline is present, including a past deadline.",
  ],
  ["Merchandise", "+10", "The update category is MERCH."],
  [
    "Irrelevant editorial",
    "−30",
    "No active linked oshi, with opinion, editorial, コラム, or 考察 in the title.",
  ],
];

export function OshiManagement() {
  const { oshi, stats, loading, error, refresh, openOshiForm } = useAppData();
  const [deleting, setDeleting] = useState<Oshi | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [mutationError, setMutationError] = useState("");
  const [notice, setNotice] = useState("");
  async function toggle(item: Oshi) {
    setBusyId(item.id);
    setMutationError("");
    try {
      await api.updateOshi(item.id, { active: !item.active });
      setNotice(`${item.name} ${item.active ? "paused" : "activated"}.`);
      refresh();
    } catch (error) {
      setMutationError(describeError(error));
    } finally {
      setBusyId(null);
    }
  }
  async function remove() {
    if (!deleting || busyId !== null) return;
    setBusyId(deleting.id);
    setMutationError("");
    try {
      await api.deleteOshi(deleting.id);
      setNotice(`${deleting.name} removed. Update history retained.`);
      setDeleting(null);
      refresh();
    } catch (error) {
      setMutationError(describeError(error));
    } finally {
      setBusyId(null);
    }
  }
  return (
    <div className="page-content management-page">
      <header className="page-header">
        <div>
          <h1>Oshi Management</h1>
          <p>Control what enters your feed.</p>
        </div>
        <div className="header-actions">
          <button className="button" onClick={refresh} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
          <button
            className="button button-primary"
            onClick={() => openOshiForm()}
          >
            + Add oshi
          </button>
        </div>
      </header>
      <div className="live-notice" role="status">
        {notice}
      </div>
      {Boolean(error) && <ErrorState error={error} retry={refresh} />}
      {mutationError && !deleting && (
        <p className="inline-error" role="alert">
          {mutationError}
        </p>
      )}
      {!error && (
        <>
          <div
            className="stats-grid"
            aria-label="Feed statistics"
            aria-busy={loading}
          >
            <StatCard
              label="Following"
              value={stats?.active_oshi}
              detail={`${stats?.total_oshi ?? "—"} tracked oshi`}
            />
            <StatCard
              label="Total updates"
              value={stats?.total_updates}
              detail="Across your entire feed"
            />
            <StatCard
              label="New updates"
              value={stats?.by_status.NEW}
              detail="Ready for your attention"
            />
            <StatCard
              label="Saved"
              value={stats?.by_status.SAVED}
              detail="Kept for later"
            />
          </div>
          <section
            className="panel oshi-panel"
            aria-labelledby="tracked-oshi-heading"
          >
            <div className="panel-heading">
              <h2 id="tracked-oshi-heading">Your oshi</h2>
              <span className="muted">{oshi.length} tracked</span>
            </div>
            {loading && !oshi.length ? (
              <div className="table-loading" role="status">
                Loading your oshi…
              </div>
            ) : oshi.length ? (
              <OshiTable
                oshi={oshi}
                edit={openOshiForm}
                remove={(item) => {
                  setDeleting(item);
                  setMutationError("");
                }}
                toggle={toggle}
                busyId={busyId}
              />
            ) : (
              <EmptyState
                title="Who are you following?"
                action={
                  <button
                    className="button button-primary"
                    onClick={() => openOshiForm()}
                  >
                    + Add oshi
                  </button>
                }
              >
                Add a favorite title, character, game, or artist.
              </EmptyState>
            )}
          </section>
        </>
      )}
      <section
        className="panel rules-panel"
        aria-labelledby="feed-rules-heading"
      >
        <div className="panel-heading">
          <div>
            <h2 id="feed-rules-heading">Feed rules</h2>
            <p>Know why an update earns your attention.</p>
          </div>
          <span className="badge">v0.1</span>
        </div>
        <div className="rules-list">
          {RULES.map(([label, points, detail]) => (
            <div className="scoring-rule" key={label}>
              <div>
                <span>{label}</span>
                <p>{detail}</p>
              </div>
              <strong
                className={points.startsWith("−") ? "negative-score" : ""}
              >
                {points}
              </strong>
            </div>
          ))}
        </div>
        <p className="rules-note">
          Each signal counts once. The final score stays between{" "}
          <strong>0 and 100</strong>. Keyword weights and oshi priority do not
          multiply these points.
        </p>
      </section>
      {deleting && (
        <Modal
          titleId="delete-title"
          onClose={() => setDeleting(null)}
          busy={busyId !== null}
        >
          <div className="modal-header">
            <h2 id="delete-title">Remove {deleting.name}?</h2>
            <button
              className="close-button"
              aria-label="Close delete confirmation"
              disabled={busyId !== null}
              onClick={() => setDeleting(null)}
            >
              ×
            </button>
          </div>
          <p className="delete-explanation">
            This removes the oshi and its keywords. Your updates will stay in
            your history, with their relevance scores refreshed.
          </p>
          {mutationError && (
            <p className="inline-error" role="alert">
              {mutationError}
            </p>
          )}
          <div className="modal-footer">
            <button
              className="button"
              disabled={busyId !== null}
              onClick={() => setDeleting(null)}
            >
              Cancel
            </button>
            <button
              className="button button-danger"
              disabled={busyId !== null}
              onClick={remove}
            >
              {busyId !== null ? "Removing…" : "Remove oshi"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
