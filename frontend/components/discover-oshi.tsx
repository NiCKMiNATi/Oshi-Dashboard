"use client";

import { useEffect, useState } from "react";
import { api, describeError } from "@/lib/api";
import type { CatalogCandidate, Oshi } from "@/lib/types";
import { Modal } from "./modal";

export function DiscoverOshi({
  onClose,
  onManual,
  onTracked,
}: {
  onClose: () => void;
  onManual: (name: string) => void;
  onTracked: (oshi: Oshi) => void;
}) {
  const [query, setQuery] = useState("");
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    candidates: CatalogCandidate[];
    error?: string;
  }>();
  const [busyId, setBusyId] = useState<number | null>(null);
  const [mutationError, setMutationError] = useState("");
  const [notice, setNotice] = useState("");
  const search = query.trim();
  const key = `${search}:${revision}`;
  useEffect(() => {
    if (!search) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api.discover(search, controller.signal).then(
        (candidates) => {
          if (!controller.signal.aborted) setResult({ key, candidates });
        },
        (error: unknown) => {
          if (!controller.signal.aborted)
            setResult({ key, candidates: [], error: describeError(error) });
        },
      );
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [search, key]);
  const loading = Boolean(search) && result?.key !== key;
  const current = result?.key === key ? result : undefined;

  async function add(candidate: CatalogCandidate) {
    if (busyId !== null || candidate.is_tracked) return;
    setBusyId(candidate.id);
    setMutationError("");
    try {
      const oshi = await api.trackEntity(candidate.id);
      setResult((previous) =>
        previous
          ? {
              ...previous,
              candidates: previous.candidates.map((item) =>
                item.id === candidate.id ? { ...item, is_tracked: true } : item,
              ),
            }
          : previous,
      );
      setNotice(`${oshi.name} is in My Oshi.`);
      onTracked(oshi);
    } catch (error) {
      setMutationError(describeError(error));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Modal
      titleId="discover-title"
      descriptionId="discover-intro"
      onClose={onClose}
      busy={busyId !== null}
    >
      <div className="modal-header">
        <div>
          <p className="eyebrow">Find your favorites</p>
          <h2 id="discover-title">Discover oshi</h2>
        </div>
        <button
          className="close-button"
          aria-label="Close discovery"
          disabled={busyId !== null}
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <div className="discover-content">
        <p id="discover-intro">
          Search by name, nickname, or the name you know.
        </p>
        <label className="sr-only" htmlFor="discover-query">
          Search oshi
        </label>
        <input
          id="discover-query"
          type="search"
          data-initial-focus
          placeholder="Search anime, characters, artists, idols, games…"
          maxLength={200}
          value={query}
          disabled={busyId !== null}
          onChange={(event) => {
            setQuery(event.target.value);
            setMutationError("");
            setNotice("");
          }}
        />
        {!search ? (
          <div className="discover-welcome">
            <p>A few names to try</p>
            <div className="discover-examples">
              {["Higedan", "ITZY", "JJK", "Gojo", "Genshin", "Hyouka"].map(
                (example) => (
                  <button
                    className="button button-small"
                    key={example}
                    onClick={() => setQuery(example)}
                  >
                    {example}
                  </button>
                ),
              )}
            </div>
            <p className="help-text">
              This first collection is small. You can always add your own.
            </p>
          </div>
        ) : loading ? (
          <p className="discover-message" role="status">
            Searching…
          </p>
        ) : current?.error ? (
          <div className="discover-message">
            <p className="inline-error" role="alert">
              {current.error}
            </p>
            <button
              className="button"
              onClick={() => setRevision((value) => value + 1)}
            >
              Try again
            </button>
          </div>
        ) : current?.candidates.length ? (
          <ul className="discover-results" aria-label="Discovery results">
            {current.candidates.map((candidate) => (
              <li className="discover-candidate" key={candidate.id}>
                <div>
                  <h3>{candidate.name}</h3>
                  <span className="type-label">{candidate.type}</span>
                  {candidate.aliases.length > 0 && (
                    <p className="discover-aliases">
                      {candidate.aliases.join(" · ")}
                    </p>
                  )}
                  {candidate.description && (
                    <p className="help-text">{candidate.description}</p>
                  )}
                </div>
                <button
                  className={`button button-small ${candidate.is_tracked ? "tracking-button" : "button-primary"}`}
                  disabled={candidate.is_tracked || busyId !== null}
                  aria-label={
                    candidate.is_tracked
                      ? `Tracking ${candidate.name}`
                      : `Add ${candidate.name}`
                  }
                  onClick={() => add(candidate)}
                >
                  {candidate.is_tracked
                    ? "✓ Tracking"
                    : busyId === candidate.id
                      ? "Adding…"
                      : "Add"}
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="discover-message" role="status">
            No matches for “{search}” in this collection.
          </p>
        )}
        {mutationError && (
          <p className="inline-error" role="alert">
            {mutationError}
          </p>
        )}
        <p className="discover-notice" role="status">
          {notice}
        </p>
        <div className="discover-footer">
          <span>Missing your favorite?</span>
          <button
            className="button"
            disabled={busyId !== null}
            onClick={() => onManual(search)}
          >
            + Add manually
          </button>
        </div>
      </div>
    </Modal>
  );
}
