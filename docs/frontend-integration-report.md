OSHI_SYNC_V1
TYPE:RESULT
DIR:X2C
PROJECT:Oshi Dashboard
VERSION:0.1
PHASE:frontend-integration
DATE:2026-09-12

## DONE

Replaced the placeholder frontend with working dashboard and oshi management routes connected to the existing FastAPI backend. The implementation uses Next.js 16, React 19, TypeScript, App Router, and plain CSS. All required frontend checks and six real-API browser tests pass.

Backend source, schemas, routes, scoring, dependency locks, and tests are unchanged, confirmed against a pre-integration SHA-256 snapshot. The personal database still contains three oshi and ten updates. Browser verification used disposable seeded SQLite databases. All verification servers were stopped afterward. Changes remain local and uncommitted; no deployment was performed.

## FILES_CHANGED

Modified existing project files during this milestone:

```text
.gitignore
AGENTS.md
README.md
docs/architecture.md
docs/implementation-report.md
frontend/app/globals.css
frontend/app/layout.tsx
frontend/app/page.tsx
frontend/package.json
frontend/package-lock.json
scripts/README.md
```

Added:

```text
docs/frontend-integration.md
docs/frontend-integration-report.md
frontend/.env.example
frontend/app/oshi/page.tsx
frontend/components/app-shell.tsx
frontend/components/dashboard.tsx
frontend/components/feed-header.tsx
frontend/components/feedback.tsx
frontend/components/modal.tsx
frontend/components/oshi-form.tsx
frontend/components/oshi-management.tsx
frontend/components/sidebar.tsx
frontend/components/status-actions.tsx
frontend/components/update-card.tsx
frontend/components/update-drawer.tsx
frontend/lib/api.ts
frontend/lib/display.ts
frontend/lib/types.ts
frontend/lib/use-api-resource.ts
frontend/lib/use-feed-filters.ts
frontend/playwright.config.ts
frontend/public/oshi/README.md
frontend/public/oshi/blue.svg
frontend/public/oshi/pink.svg
frontend/public/oshi/teal.svg
frontend/tests/integration.spec.ts
scripts/integration-backend.py
```

Next.js also regenerated `frontend/next-env.d.ts` during build/dev checks. Screenshots and test artifacts are ignored under `frontend/test-results/`. Git has no initial commit, so its status lists the entire project as untracked; the inventory above distinguishes this milestone from the earlier backend work.

## UI_IMPLEMENTED

- Persistent OSHI sidebar with actual oshi names, active/paused state, selected oshi, category navigation, Saved, and management navigation.
- Dashboard with global new-update count, search, refresh, all seven category pills, status and minimum-score filters, relevance-sorted cards, and pagination.
- Cards with category/oshi badges, score, title, summary, source/date/keyword metadata, persisted status, and Save / Interested / Ignore actions.
- Right-side detail drawer with fetched detail, available dates/location, source link, tracked oshi, text-matched keyword context, and Save / Going / Ignore actions.
- Management table with actual priorities, keyword weights, active state, add/edit forms, pause/activate, and delete confirmation. Global feed stats and all six deterministic scoring rules are visible.
- Loading, empty, request-error, API-unavailable, and retry states. No alternate network fixtures in the frontend.
- Semantic controls, visible focus, native modal focus containment, Escape/backdrop dismissal, focus restoration, and a skip link. No document overflow at 1440, 1200, 1024, or 768px; the management table scrolls within its container.

## API_CONNECTED

| Endpoint | UI use |
| --- | --- |
| `GET /api/oshi` | Sidebar, badges, keyword context, management |
| `POST /api/oshi` | Add form |
| `PATCH /api/oshi/{id}` | Edit form and active-state changes |
| `DELETE /api/oshi/{id}` | Confirmed removal |
| `GET /api/updates` | Feed, combined filters, pagination, refresh |
| `GET /api/updates/{id}` | Detail drawer |
| `PATCH /api/updates/{id}/status` | Card and drawer status actions |
| `GET /api/stats` | Counts, navigation, management stat cards |

Update creation and general update editing remain backend capabilities without new UI controls, as requested by this milestone.

Architectural decisions:

- Centralize HTTP calls and typed payloads in `frontend/lib/api.ts` and `types.ts`. Read `NEXT_PUBLIC_API_URL`, defaulting to `http://127.0.0.1:8000`; retain existing backend CORS behavior.
- Use React context for shared oshi/stats and ordinary state/hooks for forms, reads, and mutations. No runtime UI framework or state library was added. Playwright is a development dependency only.
- Keep `oshi`, `category`, `status`, and `min_score` in the URL and forward them to the existing API. Search only loaded title, summary, source, and associated oshi names, without a backend search request.
- Load 50 updates per page. Discard obsolete reads, abort on cancellation, and time out requests after ten seconds. Confirm writes with the backend before updating and refetching visible data.
- Treat backend relevance scores and single-status semantics as authoritative. Label keyword context as locally derived text matches; the API does not provide a per-update score explanation.

## TEST_RESULTS

Final frontend command sequence ran successfully from `frontend/`:

```sh
npm run lint
npm run typecheck
npm run build
npm run test:integration
```

| Check | Result |
| --- | --- |
| ESLint | Passed |
| Next route type generation + TypeScript | Passed |
| Next production build | Passed; `/`, `/oshi`, and the not-found route generated |
| Playwright against both running applications | **6 passed in 25.5s**, Google Chrome |
| Ruff check/format for `scripts/integration-backend.py` | Passed |
| npm dependency installation audit | Zero reported vulnerabilities |
| Backend snapshot comparison | No changes |

Browser tests cover real seeded data and all query filters; search without network requests; refresh; detail metadata, Escape, and focus restoration; durable Save/Going/Ignore mutations; management stats and create/edit/pause/delete; refused connections, retry, and failed writes; desktop/tablet overflow; and pagination/search across additional real API pages.

The backend's **88 passing tests and 98% coverage** are the previous milestone's baseline, documented in [implementation-report.md](implementation-report.md). The backend unit suite was not rerun during this frontend-only milestone. Real backend endpoints were exercised by the integration suite.

## MANUAL_VERIFICATION

Ran FastAPI and Next.js together against an isolated seeded database and inspected the resulting browser UI and screenshots.

| Requested behavior | Observed result |
| --- | --- |
| Seeded updates render | Ten real records, three followed oshi, three new updates; relevance order confirmed |
| Oshi filter | 原神 selected through the sidebar produced its three updates |
| Category filter | Combined 原神 + MERCH produced one update; a separate live News selection also worked |
| Status/minimum-score filters | Requests carried existing query parameters; matching and empty states worked |
| Search | Case-insensitive Ryujin search produced three loaded updates without another API request |
| Drawer | Opened from a card; actual detail/source/dates/location rendered; Escape and close restored focus |
| Status persistence | Save/Going/Ignore survived reload in browser tests; Interested was separately set through the live UI and confirmed after Refresh |
| Stats | Following 3, total updates 10, new 3, saved 2 rendered from the API |
| Backend offline | Actually stopped the FastAPI process while the browser remained open; Refresh showed the offline state with no cards or page errors |
| Backend recovery | Restarted FastAPI; Try again restored ten updates in the same browser session with no page errors |

Visual review included the drawer and management screen. Generated screenshots: `frontend/test-results/dashboard.png`, `drawer.png`, `oshi-management.png`, and `offline.png`. The additional actual-process-stop screenshot is a local review artifact at `/tmp/oshi-frontend-review/backend-stopped.png`.

## FIGMA_DEVIATIONS

The connected file exposes page **“v0.1 Wireframes”**, with [“01 Dashboard - Feed” (`2:2`)](https://www.figma.com/design/dS4aiNmBAUBURfRpKK6dgk?node-id=2-2) and [“02 Oshi Management” (`2:116`)](https://www.figma.com/design/dS4aiNmBAUBURfRpKK6dgk?node-id=2-116). The requested **“v0.1 Prototype” / “01 Dashboard”** names were not available. Both accessible frames were inspected using Figma design context and screenshots before implementation; exact fidelity to the unavailable prototype cannot be claimed.

- Preserved the supplied dark palette, desktop sidebar, feed cards, management table, and right-side detail layout using flexible CSS.
- Drawer width is 390px rather than the reference 360px to accommodate real Japanese titles and metadata. System fonts avoid runtime font downloads.
- Real numeric priorities, all category/status/score filters, additional stats, keyword weights, CRUD forms, and error/loading states extend the static reference.
- Calendar navigation was omitted because only `/` and `/oshi` were authorized; category navigation and Saved use existing feed filters.
- Oshi markers use exact downloaded Figma SVG exports. No anime artwork or invented network records were added; backend demo labels remain visible.

## BACKEND_ISSUES

No integration defect or contract mismatch requiring a backend change was found. The API supplies linked oshi IDs and their tracked keywords, but no explicit per-update match list or score breakdown. The UI clearly labels text matches as derived context and displays the stored relevance score unchanged.

## BLOCKERS

No functional blockers remain for this milestone. Comparing against the specifically named high-fidelity prototype requires access to that page or its node link. Browser tests require installed Google Chrome and free ports 3000/8000, as documented.

## NEXT

Start the local application with `./scripts/dev-backend.sh` and, in another terminal, `npm --prefix frontend run dev`. Open `http://127.0.0.1:3000` and `/oshi` for review. When the named prototype becomes available, review the two screens against it for any remaining visual differences.

MSN ingestion, authentication, deployment, PostgreSQL, light mode, and the reserved CLI commands remain outside this milestone.
