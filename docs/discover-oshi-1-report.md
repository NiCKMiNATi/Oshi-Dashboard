OSHI_SYNC_V1  
TYPE:RESULT  
PROJECT:Oshi Dashboard  
VERSION:0.1  
PHASE:discover-oshi-1

## DONE

Added local discovery, canonical tracking, safe remove/re-add, and manual fallback. Both Add oshi entry points now open a search-first modal. Existing dashboard behavior, personal data, and public Oshi/update contracts are preserved. No external provider, dependency, framework, or recommendation system was added.

## FILES_CHANGED

Files changed in this phase:

| File | Purpose |
| --- | --- |
| `backend/app/models.py` | Catalog entities, aliases, and optional tracking links as new tables. |
| `backend/app/catalog.py` | Eight local entries, idempotent metadata seed, Unicode search ranking, and existing-following recognition. |
| `backend/app/routes/discover.py` | Search and atomic track endpoints. |
| `backend/app/schemas.py` | Typed discovery candidate response. |
| `backend/app/main.py` | Register discovery routes and initialize only missing catalog metadata at startup. |
| `backend/tests/test_discover.py` | 38 backend discovery checks. |
| `backend/tests/test_app.py` | Include the two additive endpoints in OpenAPI assertions. |
| `frontend/components/discover-oshi.tsx` | Debounced search, result cards, tracking, errors/retry, and manual fallback. |
| `frontend/components/app-shell.tsx` | Shared discovery/manual/edit flow and immediate cache updates after confirmed tracking. |
| `frontend/components/oshi-form.tsx` | Prefilled manual names and progressive priority/weight controls; retain full editing. |
| `frontend/components/modal.tsx` | Escape dismissal from search inputs, respecting IME composition. |
| `frontend/lib/api.ts` | Centralized typed discover/track requests. |
| `frontend/lib/types.ts` | Catalog candidate type. |
| `frontend/app/globals.css` | Discovery and simplified manual form styling. |
| `frontend/tests/discovery.spec.ts` | Four real-API browser discovery scenarios. |
| `frontend/tests/integration.spec.ts` | Reach the existing creation test through discovery/manual fallback and More options. |
| `AGENTS.md` | Preserve catalog/tracking separation in future work. |
| `README.md` | Discovery usage, manual fallback, and startup metadata behavior. |
| `data/README.md` | New tables and personal-data boundaries. |
| `docs/api.md` | Search/track inputs, output, ranking, status codes, and identity rules. |
| `docs/architecture.md` | Additive schema, identity links, startup, and duplicate prevention. |
| `docs/frontend-integration.md` | Search UX, state, manual fallback, and verification scope. |
| `docs/local-cli.md` | Clarify catalog-only metadata initialization at startup. |
| `docs/discover-oshi-1-report.md` | This report. |

Git status was inspected before changes. Earlier uncommitted CLI/UI work is preserved. This phase remains uncommitted; the existing checkpoint is `8df06a0`.

## CATALOG_MODEL

`CatalogEntity` contains ID, canonical name, existing Oshi type, provider, nullable external ID/description, and creation timestamp. `EntityAlias` contains its own ID, entity ID, alias, and normalized alias. `CatalogTracking` optionally links one entity to one personal Oshi; it keeps identity through renames without altering the original Oshi table.

The bundled local collection has eight entries and seventeen aliases: Official髭男dism, ITZY, 進撃の巨人, 原神, 呪術廻戦, 五条悟, 氷菓, and 内田雄馬. ITZY uses the existing `ARTIST` type with a group description. Local provider IDs are stable seed slugs. Unique provider/ID and entity/normalized-alias constraints make insertion idempotent. Startup inserts missing catalog metadata only and preserves existing metadata edits. This is discovery metadata, not update/news content.

Deleting a personal Oshi removes its optional identity link but cannot remove catalog entries or aliases. The existing manual-create endpoint remains independent.

## SEARCH_BEHAVIOR

`GET /api/discover?q=...` searches canonical names and aliases after Unicode NFKC normalization, case folding, and whitespace removal. Ranking is canonical exact → alias exact → canonical prefix → alias prefix → canonical substring → alias substring, with deterministic name/ID ties. Empty queries return an empty array. The query limit is 200 characters; results default to 20, capped at 50. Literal SQL wildcard characters have no wildcard meaning.

Candidates contain ID, name, type, description, aliases, provider, and `is_tracked`. Explicit identity links take precedence; otherwise same-type normalized canonical/alias names recognize existing manual or legacy rows. Paused Oshi count as already tracked and are not reactivated. Multiple pre-existing matching rows are not merged; the lowest ID is reused. Cross-type names remain distinct.

The frontend debounces for 250ms, cancels obsolete requests, hides obsolete results, and provides loading, no-match, error, and retry states. Search shortcuts only fill the query; candidate data always comes from the real API. Search intentionally has no typo correction, inferred transliteration, semantic matching, or external provider access.

## TRACK_FLOW

`POST /api/discover/{entity_id}/track` creates an ordinary Oshi using canonical name/type, priority 50, active true, and canonical/alias keywords at weight 1. A unique optional catalog link records identity. SQLite obtains its write reservation before checking tracking state, preventing concurrent discovery Add requests from creating duplicate rows.

Creation returns 201; an already tracked item returns the unchanged existing Oshi with 200. Existing priority, active state, names, and keywords are never overwritten. Unknown IDs return 404. After success, shared sidebar/management data updates immediately, stats/feed refresh, and the result becomes disabled Tracking without a page reload.

Both Higedan and ITZY passed the complete browser flow: search → add → sidebar → remove → disappear → search again → re-add. Old updates are retained; deleting and re-adding does not restore their former Oshi associations automatically.

## MANUAL_ADD

Add manually is always available, including no-match states, and pre-fills the search text. The existing form accepts name, type, and optional aliases/keywords through `POST /api/oshi`. More options exposes priority, active state, and keyword weights; editing retains full controls. Manual entries do not require or create catalog records. Cancel returns to discovery; success refreshes the following and management data.

## TEST_RESULTS

Final verification:

| Command/check | Result |
| --- | --- |
| `./scripts/test-backend.sh scripts/tests --cov=app --cov-report=term-missing` | **143 passed**: 126 backend + 17 CLI; **99% backend coverage**. |
| `backend/.venv/bin/ruff check backend` | Pass. |
| `backend/.venv/bin/ruff format --check backend` | Pass. |
| `npm --prefix frontend run lint` | Pass. |
| `npm --prefix frontend run typecheck` | Pass. |
| `npm --prefix frontend run build` | Pass; `/` and `/oshi` generated. |
| `npm --prefix frontend run test:integration` | **14 passed**, 48.8 seconds: all ten existing scenarios plus four discovery scenarios. |
| `git diff --check` | Pass. |

Backend tests cover all requested example queries, exact/prefix/substring ranking, case/Unicode/whitespace, empty/invalid input, tracking recognition/defaults/duplicates, concurrent Add, renaming, removal/history/catalog survival, re-tracking, seed idempotency, and startup from the old four-table schema.

Browser tests cover Higedan and ITZY removal/re-add, Tracking state, sidebar/management/stats updates, independent manual fallback, debounce, late-response cancellation, and failed search/add recovery. The first browser run exposed native search input behavior consuming Escape to clear the query; modal key handling fixed dismissal, and the final complete suite passed. Existing filters, status persistence, CRUD, pagination, source behavior, offline states, and layout checks still pass.

Read-only local browser review confirmed all eleven requested query examples, recognition of existing 原神/進撃の巨人 following, initial focus, Escape, manual Cancel, and discovery layout at 768/1024/1200/1440 pixels. No browser page errors or personal mutation requests occurred. Screenshots and browser measurements are in ignored `.runtime/discover-oshi-1/`; integration screenshots are in `frontend/test-results/`.

## PERSONAL_DATA_SAFETY

Before changes, CLI-owned services were stopped and a SQLite backup was created at `.runtime/discover-oshi-1/personal-before.db`, with a SQL snapshot beside it. Tests used only disposable SQLite databases through the existing test configuration.

After normal local startup, a read-only comparison against that backup confirmed identical original table definitions and all original rows: **3 Oshi, 9 keywords, 10 updates, 9 update associations**. The only additions were the three catalog tables, 8 catalog entities, and 17 aliases; catalog tracking remained empty because no personal Add operation was performed. SQLite integrity and foreign-key checks passed. Results are recorded in `.runtime/discover-oshi-1/database-verification.json`.

Both local services were restored from outside the repository via the installed CLI and remain running at `http://localhost:8000` and `http://localhost:3000`.

## BLOCKERS

None for this milestone. The local collection is intentionally small, and external catalogs/news ingestion remain outside scope. Manual creation supports favorites absent from the collection.

## NEXT

Run `oshi hiraku`, choose + Add oshi, and try Higedan or ITZY. Review the new flow and create a Git checkpoint for the accumulated local CLI/UI/discovery work before the next milestone.
