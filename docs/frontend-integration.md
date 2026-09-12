# Frontend integration

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

The dashboard shows category and oshi badges, the backend relevance score, title, summary, source, published date, text-matched tracked keywords, and the persisted status. Clicking anywhere on a card’s non-action area opens the detail drawer through a semantic button. Card actions set `SAVED`, `INTERESTED`, or `IGNORED`; drawer actions set `SAVED`, `GOING`, or `IGNORED`. These are single backend statuses, not independent toggles. Select another action to change a status; clicking an already selected action keeps it selected.

The drawer requests `/api/updates/{id}` and displays all available date/location fields, tracked oshi, source link, and keyword context. Native dialogs provide modal focus containment, Escape/backdrop dismissal, visible close buttons, and focus restoration. Date-only event fields preserve their calendar date; timestamps display the browser’s local timezone.

Oshi management supports create, full edit (including keyword weights), active-state changes, and explicit delete confirmation. Deletion preserves updates as specified by the backend. Weights are shown and editable from 0–100; the UI does not reinterpret their magnitude as bonus points. Stats are global, as is the header’s new-update count.

## Filters and pagination

`oshi`, `category`, `status`, and `min_score` are validated against the supported values, stored in the route query string, and forwarded to `GET /api/updates`. Missing filters remain omitted. Initial results request 50 rows. “Load more updates” requests another page and keeps the combined results in descending relevance order. An exact full page may offer one additional load before discovering the end of the feed.

Search matches Unicode-normalized, case-insensitive title, summary, source, and associated oshi names over the rows already loaded. It sends no search request to the backend. When more pages exist, the UI explicitly states the scope of the search. Changing server filters resets pagination. Refresh refetches the shared oshi/stats data, current feed pages, and an open detail drawer.

## Data and error handling

All HTTP calls are centralized in `frontend/lib/api.ts`. The client has a ten-second timeout, JSON validation error messages, cancellation for obsolete reads, and a dedicated API-unavailable error. React hooks discard aborted results so a late response cannot replace a newer filter selection. Mutations wait for server confirmation and then refetch; failed mutations leave persisted UI state unchanged and show an error.

Loading skeletons, empty results, inline mutation errors, offline messages, and retry controls are functional states. There are no frontend fixtures or alternate network data. Seeded `[DEMO]` titles and fictional notices remain visible because they are part of the real backend records.

The backend returns oshi IDs and keywords, but no per-update match list or score explanation. The drawer therefore labels the locally derived context “Keyword matches in this text.” This is display context only; the backend’s `relevance_score` remains authoritative. JavaScript NFKC/lowercase substring matching covers the seeded Japanese/Latin data; Python case folding may differ for less common Unicode characters. No semantic relevance explanation is invented.

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

See [the result report](frontend-integration-report.md) for commands, observed results, design deviations, and remaining scope.
