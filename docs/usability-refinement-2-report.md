OSHI_SYNC_V1  
TYPE:RESULT  
PROJECT:Oshi Dashboard  
VERSION:0.1  
PHASE:usability-refinement-2

## DONE

Simplified the existing dashboard and drawer, made removal visible and safe for every tracked oshi, and disabled fictional source links. Existing filters, status persistence, editing, and the local CLI remain functional. No dependencies were added.

## FILES_CHANGED

Files changed in this phase:

| File | Change |
| --- | --- |
| `frontend/components/update-card.tsx` | Essential card content, one important date, no source/keyword metadata, subtle score. |
| `frontend/components/update-drawer.tsx` | Overview, conditional Action, Source, collapsed context, and four status actions. |
| `frontend/components/status-actions.tsx` | Interested in the drawer; persisted current status remains visible. |
| `frontend/lib/display.ts` | Explicit demo-source detection and validation of external source URLs. |
| `frontend/components/oshi-management.tsx` | Clear Edit/Remove actions, simpler table, history-preserving confirmation. |
| `frontend/components/modal.tsx` | Described confirmation, initial Cancel focus, and explicit keyboard focus wrapping. |
| `frontend/components/app-shell.tsx` | Immediate shared-cache removal, selected-filter cleanup, and API refresh. |
| `frontend/components/sidebar.tsx` | Preserve selected oshi context when opening management. |
| `frontend/lib/use-api-resource.ts` | Small cache-update callback for confirmed deletion. |
| `frontend/app/globals.css` | Simpler card hierarchy, grouped drawer, and management action styling. |
| `frontend/tests/integration.spec.ts` | Preserve six existing tests and add four usability tests. |
| `docs/frontend-integration.md` | Current behavior and integration details. |
| `README.md` | Removal instructions, demo-source behavior, and this report. |
| `docs/usability-refinement-2-report.md` | This handoff. |

The working tree also contains preserved CLI and first UI-refinement changes from earlier milestones. The existing checkpoint is `8df06a0` (completed backend/frontend integration); this phase is uncommitted. No earlier work was discarded.

## CARD_SIMPLIFICATION

Cards retain category and oshi badges, title, a maximum two-line summary, status/actions, and a subdued numeric relevance score. Deadlines take precedence over start dates; location appears only when supplied. Relevant event/release starts are shown when no deadline exists. Full ranges, publisher, published timestamp, keywords, and context are in the drawer.

Compact deadlines use the browser's local time; full timestamps and timezone remain in the accessible label, tooltip, and drawer. Date-only events preserve their calendar date. No relevance calculation changed.

## DRAWER_SIMPLIFICATION

The drawer groups Overview, Action, Source, and “Why this appeared.” Empty fields and empty Action sections are omitted. Context is collapsed initially and displays the backend score plus locally found tracked keywords when available. It does not invent a backend scoring explanation. Save, Interested, Going, and Ignore all use the existing status API.

Keyboard opening, Escape dismissal, visible focus, Tab containment, and focus restoration remain available.

## OSHI_REMOVAL

Every management row has Edit and Remove. Removal asks “Remove {name} from My Oshi?” and explains: “You'll stop tracking new updates for this oshi. Existing update history will remain.” Cancel receives initial focus. Escape or Cancel dismisses without a mutation; failed requests keep the oshi visible with an error.

Successful `DELETE /api/oshi/{id}` immediately removes the item from the shared sidebar/table cache, clears its selected query parameter, and refreshes oshi/stats. The shared revision causes the feed to refetch when displayed. No page reload is required. Existing backend deletion semantics preserve update rows and remove their association with the removed oshi; deletion is not replaced with deactivation.

The table has only Oshi, Type, Priority, Keywords, Active, and Actions. Keyword weights remain editable and available in tooltips, without extra numbers in each keyword badge.

## SOURCE_LINK_FIX

The existing seed metadata `source: "Demo fixture (fictional)"` is a reliable signal. Demo detection uses that explicit source value, not the title or `[DEMO]` prefix. Demo drawers show a disabled “Demo source” button and a fictional-sample explanation, with no external anchor.

Real HTTP(S) links retain the exact API `source_url` and use `target="_blank"` with `rel="noopener noreferrer"`. Missing, empty, invalid, or unsupported-protocol URLs cannot become source links. Missing source handling is defensive frontend behavior; the stable API still requires a URL. No fixture flag or API change was necessary.

## TEST_RESULTS

Final verification after the focus fixes:

| Command | Result |
| --- | --- |
| `npm --prefix frontend run lint` | Pass |
| `npm --prefix frontend run typecheck` | Pass |
| `npm --prefix frontend run build` | Pass; `/` and `/oshi` generated |
| `npm --prefix frontend run test:integration` | **10 passed**, 38.4 seconds |
| `git diff --check` | Pass |

The existing Playwright configuration launches the real FastAPI application against disposable SQLite and the real Next.js frontend in Chrome. No second test configuration was added.

The suite covers filters, client search, refresh, durable status changes, oshi CRUD, errors/offline recovery, pagination, and widths 768/1024/1200/1440. New checks cover removal confirmation, Cancel/Escape, focus, failed deletion, immediate sidebar/table removal while the next list request is held, selected-filter cleanup, refreshed stats, and preservation of linked update history. Source checks distinguish metadata from titles, verify no demo navigation, preserve an exact real URL/new-tab attributes, and exercise missing URLs. Card checks confirm key fields and two-line summaries while secondary details remain accessible in the drawer.

Testing exposed Cancel focus before native dialog opening and Tab escaping to browser chrome; explicit initial focus after `showModal()` and Tab wrapping resolved both. The final complete run passed. Backend and CLI code were unchanged, so their earlier baselines were not rerun for this frontend phase.

## MANUAL_VERIFICATION

After the isolated suite, both services were restored through `oshi kaishi` from `/tmp`. Read-only browser walkthroughs and visual screenshot review confirmed:

- All 10 personal demo updates and all 3 tracked oshi render from the local API.
- Dashboard and management have no document overflow at 768, 1024, 1200, and 1440 pixels. The narrow management table scrolls within its container.
- The drawer opens with context collapsed; Demo source is disabled; Escape closes it and restores focus.
- Management presents clear Edit/Remove buttons. Cancel receives focus; reverse Tab stays in the confirmation; Cancel closes it. No removal or status mutation was sent to the personal database.
- No browser page errors occurred during the walkthrough.
- A read-only SQLite SQL-dump comparison against `.runtime/database-before-usability-2.sql` confirmed that personal schema and rows are unchanged. No personal reseeding occurred.

Screenshots and measurements are in ignored `.runtime/usability-refinement-2/`: dashboard and management at 1440/768, the drawer, removal confirmation, and `verification.json`. Integration screenshots remain in ignored `frontend/test-results/`.

Final `oshi status` confirms API `http://localhost:8000` and frontend `http://localhost:3000` running, with SQLite present. Services are left running for review.

## BACKEND_CHANGES

None. Models, schemas, seed data, scoring, API contracts, and history-preserving deletion behavior are unchanged.

## BLOCKERS

None for this milestone. Current sample announcements remain fictional; there is no real ingestion in scope.

## NEXT

Use `oshi hiraku` to review the simplified feed. Remove any unwanted following through Oshi Management → Remove when desired. The implementation itself did not remove any personal oshi. A new Git checkpoint can capture this milestone together with the preserved local CLI/UI work after review.
