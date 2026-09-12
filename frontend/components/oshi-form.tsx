"use client";

import { useState } from "react";
import { api, describeError } from "@/lib/api";
import { normalize } from "@/lib/display";
import {
  OSHI_TYPES,
  type Oshi,
  type OshiInput,
  type OshiType,
} from "@/lib/types";
import { Modal } from "./modal";

export function OshiForm({
  oshi,
  onClose,
  onSaved,
}: {
  oshi?: Oshi;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(oshi?.name ?? "");
  const [type, setType] = useState<OshiType>(oshi?.type ?? "OTHER");
  const [priority, setPriority] = useState(String(oshi?.priority ?? 50));
  const [active, setActive] = useState(oshi?.active ?? true);
  const [keywords, setKeywords] = useState(
    () =>
      oshi?.keywords.map((item) => ({
        value: item.value,
        weight: String(item.weight),
      })) ?? [],
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const normalized = keywords.map((item) => normalize(item.value));
    if (
      normalized.some((value) => !value) ||
      new Set(normalized).size !== normalized.length
    ) {
      setError(
        "Keywords must be nonblank and unique, ignoring case and character width.",
      );
      return;
    }
    if (!name.trim()) {
      setError("Please enter an oshi name.");
      return;
    }
    const input: OshiInput = {
      name: name.trim(),
      type,
      priority: Number(priority),
      active,
      keywords: keywords.map((item) => ({
        value: item.value.trim(),
        weight: Number(item.weight),
      })),
    };
    setBusy(true);
    setError("");
    try {
      if (oshi) await api.updateOshi(oshi.id, input);
      else await api.createOshi(input);
      onSaved();
    } catch (error) {
      setError(describeError(error));
      setBusy(false);
    }
  }
  return (
    <Modal titleId="oshi-form-title" onClose={onClose} busy={busy}>
      <div className="modal-header">
        <div>
          <p className="eyebrow">Your following</p>
          <h2 id="oshi-form-title">{oshi ? "Edit oshi" : "Add an oshi"}</h2>
        </div>
        <button
          className="close-button"
          aria-label="Close oshi form"
          disabled={busy}
          onClick={onClose}
        >
          ×
        </button>
      </div>
      <form className="oshi-form" onSubmit={submit}>
        <p className="form-intro">
          Make room for what you love. Fine-tune the keywords that matter to
          you.
        </p>
        <fieldset disabled={busy}>
          <label>
            Name
            <input
              autoFocus
              name="name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={200}
              required
              placeholder="e.g. 進撃の巨人"
            />
          </label>
          <div className="form-columns">
            <label>
              Type
              <select
                aria-label="Type"
                name="type"
                value={type}
                onChange={(event) => setType(event.target.value as OshiType)}
              >
                {OSHI_TYPES.map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
            <label>
              Priority
              <input
                name="priority"
                type="number"
                min={0}
                max={100}
                step={1}
                required
                value={priority}
                onChange={(event) => setPriority(event.target.value)}
              />
            </label>
          </div>
          <p className="help-text">
            Priority is 0–100 and controls your oshi list order. It doesn’t
            multiply relevance points.
          </p>
          <label className="checkbox-label">
            <input
              name="active"
              type="checkbox"
              checked={active}
              onChange={(event) => setActive(event.target.checked)}
            />
            <span>
              Actively following
              <small>
                Paused oshi stay in your history and contribute no oshi or
                keyword points.
              </small>
            </span>
          </label>
          <div className="keyword-field-header">
            <label id="keyword-list-label">Tracked keywords</label>
            <button
              className="text-button"
              type="button"
              disabled={keywords.length >= 100}
              onClick={() =>
                setKeywords((items) => [...items, { value: "", weight: "1" }])
              }
            >
              + Add keyword
            </button>
          </div>
          <p className="help-text">
            Any matching keyword with weight above 0 adds +25 once. Weight 0
            disables it.
          </p>
          <div className="keyword-fields" aria-labelledby="keyword-list-label">
            {keywords.map((keyword, index) => (
              <div className="keyword-field" key={index}>
                <input
                  aria-label={`Keyword ${index + 1}`}
                  placeholder="Keyword or alternate name"
                  value={keyword.value}
                  required
                  maxLength={200}
                  onChange={(event) =>
                    setKeywords((items) =>
                      items.map((item, i) =>
                        i === index
                          ? { ...item, value: event.target.value }
                          : item,
                      ),
                    )
                  }
                />
                <input
                  aria-label={`Keyword ${index + 1} weight`}
                  type="number"
                  min={0}
                  max={100}
                  required
                  step={1}
                  value={keyword.weight}
                  onChange={(event) =>
                    setKeywords((items) =>
                      items.map((item, i) =>
                        i === index
                          ? { ...item, weight: event.target.value }
                          : item,
                      ),
                    )
                  }
                />
                <button
                  type="button"
                  className="close-button"
                  aria-label={`Remove keyword ${index + 1}`}
                  onClick={() =>
                    setKeywords((items) => items.filter((_, i) => i !== index))
                  }
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          {!keywords.length && (
            <p className="empty-keywords">
              No keywords yet. You can add them whenever you like.
            </p>
          )}
        </fieldset>
        {error && (
          <p className="inline-error" role="alert">
            {error}
          </p>
        )}
        <div className="modal-footer">
          <button
            className="button"
            type="button"
            disabled={busy}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="button button-primary"
            type="submit"
            disabled={busy}
          >
            {busy ? "Saving…" : oshi ? "Save changes" : "Add oshi"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
