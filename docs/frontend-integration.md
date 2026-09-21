# Frontend integration

Manual `oshi fetch` ingestion now creates ordinary backend Updates. The existing UI
needs no ingestion-specific route or API change: start the dashboard or use Refresh to
load them. Source configuration is local-file based; there is no source-management UI
or scheduled fetching. See [ingestion.md](ingestion.md).

The dark-only UI uses Next.js 16, React 19, TypeScript, App Router, and plain CSS. `/` is the dashboard; `/oshi` manages your following. The FastAPI contract is unchanged.

## Running locally

```sh
./scripts/dev-backend.sh
# In another terminal:
npm --prefix frontend run dev
```

Open `http://127.0.0.1:3000`. API data defaults to `http://127.0.0.1:8000`. Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` to change it and restart Next.js. The value is public and embedded at build time. The stable backend allows browser origins on port 3000 for localhost/127.0.0.1. No proxy or CORS contract change was added.

## Screens and state

The shared `AppShell` loads oshi and global stats. Its sidebar persists across route navigation and displays real names and active/paused states. Category navigation links open a filtered feed. Saved navigation uses the `SAVED` status. Calendar was omitted because this milestone contains only two routes and has no calendar UI.

The dashboard shows category and oshi badges, title, a summary limited to two lines, and persisted status actions. A short line below the title shows location and one important date when present: the deadline takes precedence over the start date for events, collaborations, movies, and releases. Source, published date, keyword context, and full date ranges live in the drawer. Clicking anywhere on a card’s non-action area opens the detail drawer through a semantic button. Card actions set `SAVED`, `INTERESTED`, or `IGNORED`; drawer actions also offer `GOING`. These are single backend statuses, not independent toggles. Select another action to change a status; clicking an already selected action keeps it selected.

Relevance stays visible as subdued text beside the actions: HIGH (80–100), MEDIUM (50–79), or LOW (0–49), followed by the unchanged numeric score. These groups are presentation choices only. Card deadlines use a compact local date/time; the full timestamp and timezone remain available in the accessible label, tooltip, and drawer. Event date-only values keep their calendar dates. Selected action buttons show persisted states; other statuses sit alongside the actions. Semantic native selects have matching dark pill styling, and Oshi Management has a separate labeled Manage section. See [the latest usability report](usability-refinement-2-report.md).

The drawer requests `/api/updates/{id}` and groups information into Overview, Action, Source, and a collapsed “Why this appeared” disclosure. Empty summaries, dates, locations, and keyword lists are omitted. Action is omitted when no action fields exist. Native dialogs provide Escape/backdrop dismissal, visible close buttons, and focus restoration, with explicit Tab wrapping among visible controls. Backdrop dismissal requires a press and release outside the actual dialog bounds: clicking text or blank space inside, or dragging from inside to outside, keeps the preview open. The preview glides 56px from the right with a subtle 0.985-to-1 scale settle over 420ms; its opacity and backdrop fade in separately over 180–200ms. Closing reverses the short glide over 220ms and fades out over 200ms. Dismissal completes when the panel becomes transparent, so the invisible tail of the movement does not delay interaction; refreshes do not restart the fallback timer. Closing during entry reverses from the current position. Entry begins after the native dialog is shown and painted; dismissal waits for exit before removing the dialog and restoring focus, with a fallback for cancelled or absent transitions. Reduced-motion preferences disable these transitions. Date-only event fields preserve their calendar date; timestamps display the browser’s local timezone.

Oshi management shows Oshi, Type, Priority, Keywords, Active, and Actions, with visible Edit and Remove buttons for every row. Create, full edit (including keyword weights), and active-state changes remain available. Remove opens a confirmation explaining that update history remains; Cancel receives initial focus. Only a successful `DELETE /api/oshi/{id}` removes the item from the shared cache immediately, clears its selected query filter, and triggers oshi/stats/feed refresh. Failed deletion leaves the item in place. Keyword weights remain editable from 0–100 and available as table tooltips, without extra numeric labels in the table. Stats are global, as is the header’s new-update count.

The preview leaves the feed scrollable with the wheel or trackpad over the feed. Long preview details scroll independently; reaching their edge does not move the feed, and the sticky preview header keeps the close button available. Closing restores keyboard focus without scrolling back to the original card. Discovery and editing/confirmation dialogs continue to lock page scrolling.

## Discover and manual creation

Both **+ Add oshi** entry points open a shared Discover modal. Search requests use `GET /api/discover?q=...` through the typed client, debounced by 250ms. Query changes cancel obsolete requests and hide old results; loading, no-match, search-error/retry, and add-error states are explicit. Initial example buttons are query shortcuts, not fake result data. The eight-entity collection comes from the local backend only.

Candidates show canonical name, type, aliases, short description, and Add or disabled Tracking. `POST /api/discover/{id}/track` supplies the persisted Oshi; the sidebar/table cache updates immediately and shared stats/feed refresh. Discovery remains open with Tracking shown, allowing another search. Existing paused Oshi are recognized as tracked without reactivation. The optional backend identity link keeps tracking through renames; removal leaves the candidate available to re-add.

**+ Add manually** is always available, including no-match and error states. It opens the existing Oshi form with the search text prefilled, using `POST /api/oshi`. Name, type, and optional aliases/keywords are primary; More options exposes priority, active state, and weights. Editing retains the full form. Manual entries need no catalog record. Cancel returns to discovery; successful creation closes the flow and refreshes shared data.

Search receives initial focus. Escape closes the dialog even from a nonempty search input, without interrupting an active IME composition. Native modal behavior and explicit keyboard wrapping retain focus within the flow. See [the discovery report](discover-oshi-1-report.md).

## Filters and pagination

`oshi`, `category`, `status`, and `min_score` are validated against the supported values, stored in the route query string, and forwarded to `GET /api/updates`. Missing filters remain omitted. Initial results request 50 rows. “Load more updates” requests another page and keeps the combined results in descending relevance order. An exact full page may offer one additional load before discovering the end of the feed.

Search matches Unicode-normalized, case-insensitive title, summary, source, and associated oshi names over the rows already loaded. It sends no search request to the backend. When more pages exist, the UI explicitly states the scope of the search. Changing server filters resets pagination. Refresh refetches the shared oshi/stats data, current feed pages, and an open detail drawer.

## Data and error handling

All HTTP calls are centralized in `frontend/lib/api.ts`. The client has a ten-second timeout, JSON validation error messages, cancellation for obsolete reads, and a dedicated API-unavailable error. React hooks discard aborted results so a late response cannot replace a newer filter selection. Mutations wait for server confirmation and then refetch; failed mutations leave persisted UI state unchanged and show an error.

Loading skeletons, empty results, inline mutation errors, offline messages, and retry controls are functional states. There are no frontend fixtures or alternate network data. Seeded `[DEMO]` titles and fictional notices remain visible because they are part of the real backend records.

The seed module’s explicit source metadata, `Demo fixture (fictional)`, identifies demo updates without parsing titles. Their drawer shows a disabled “Demo source” button and a fictional-data explanation, with no external link. Real HTTP(S) source links preserve the exact API URL and use `target="_blank"` with `rel="noopener noreferrer"`. Missing or invalid URLs show disabled “Source unavailable”; no API change was needed.

The backend returns oshi IDs and keywords, but no per-update match list or score explanation. The drawer therefore labels the locally derived context “Keywords found in this update,” inside “Why this appeared.” This is display context only; the backend’s `relevance_score` remains authoritative. The disclosure appears only when there is a positive score, linked oshi, or matching keyword context. JavaScript NFKC/lowercase substring matching covers the seeded Japanese/Latin data; Python case folding may differ for less common Unicode characters. No semantic relevance explanation is invented.

The scoring reference shows all six backend rules, including merchandise +10, the nonstacking bonuses, and the 0–100 clamp. The source of truth remains [scoring.md](scoring.md).

## Design source

The connector exposes file `dS4aiNmBAUBURfRpKK6dgk`, page `0:1` (“v0.1 Wireframes”), frame `2:2` (“01 Dashboard - Feed”) and frame `2:116` (“02 Oshi Management”). Both were read with Figma design context and screenshot output before implementation. The requested “v0.1 Prototype” / “01 Dashboard” names were not present in the connected file.

The UI retains the accessible layout and supplied colors, using flexible CSS instead of absolute coordinates. The drawer is 390px rather than the reference 360px to fit real dates and Japanese titles. Interactive controls, full category/status filters, search, stats cards, keyword weights, and CRUD forms extend the static reference. System fonts avoid runtime font downloads. The three oshi markers are exact downloaded Figma SVG exports, not redrawn icons. No anime artwork is used.

The desktop sidebar is 240px at the primary target. Below 1200px it narrows, toolbars wrap, and the management table scrolls inside its own container. The page avoids horizontal overflow at narrower desktop/tablet widths.

## Verification

```sh
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
npm --prefix frontend run test:integration
```

Browser checks use Playwright and installed Google Chrome. Stop dev servers first: the test configuration requires free ports 3000 and 8000 and never reuses a running server. `scripts/integration-backend.py` seeds a temporary SQLite database and runs the real FastAPI application. No personal data is changed. Generated screenshots/traces live in ignored `frontend/test-results/`.

See [the original integration report](frontend-integration-report.md) for design deviations, [the usability report](usability-refinement-2-report.md) for simplification, and [the discovery report](discover-oshi-1-report.md) for current checks. Browser tests cover filters, search, status persistence, CRUD, pagination, request failures, offline states, removal/history preservation, source links, and card/drawer details. Discovery adds search → track → remove → search → re-add, manual fallback, debounce, cancellation, and error recovery checks.
