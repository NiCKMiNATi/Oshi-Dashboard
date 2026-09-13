OSHI_SYNC_V1
TYPE:RESULT
DIR:X2C
PROJECT:Oshi Dashboard
VERSION:0.1
PHASE:ui-refinement-1
DATE:2026-09-12

## DONE

Refined the existing running dashboard to emphasize deadlines, event dates, and location while retaining its dark theme, components, API integration, demo labels, and supported widths. The earlier local CLI milestone is also complete; its installation, process verification, and results are in [local-cli-report.md](local-cli-report.md).

## FILES_CHANGED

UI implementation changes are limited to:

```text
frontend/components/update-card.tsx
frontend/components/status-actions.tsx
frontend/components/feed-header.tsx
frontend/components/sidebar.tsx
frontend/app/globals.css
```

Documentation: `README.md`, `docs/frontend-integration.md`, and this report. The backend, API client, dependencies, management/forms, drawer component, and existing browser tests were not modified for this refinement. Separate CLI milestone files are inventoried in its report. Before the CLI work, the completed application was checkpointed in commit `8df06a0`; subsequent milestone changes remain local and uncommitted.

## UI_CHANGES

- Dated/located cards use a 210px right-hand section for deadline, starts/ends, and location. Missing fields produce no empty rows or placeholders. Undated cards keep the compact full-width content layout.
- At feed widths of 760px or less, that section stacks below the title, before the summary and source metadata. CSS container sizing also handles the reduced space when the detail drawer is open.
- Deadline text uses restrained warm emphasis and larger type than source metadata. It includes calendar date/year plus local 24-hour time and timezone. Event calendar dates remain date-only.
- Replaced raw “Priority 100” text with small, subdued HIGH / MEDIUM / LOW badges retaining the exact backend score.
- Selected Save/Interested/Ignore buttons represent the persisted status without repeating a separate label. Going, Bought, and New sit immediately beside the action controls.
- Status and Minimum score retain semantic native selects with pill borders, consistent dark fills, a small chevron, and visible keyboard focus.
- Oshi Management sits under a separate “Manage” heading and divider. Existing navigation destinations are unchanged.
- `[DEMO]`, `Demo fixture (fictional)`, and fictional summary notices remain visible. No artwork, gradients, light mode, or new framework was added.

## BEHAVIOR_CHANGES

Presentation only. Filtering, search scope, feed ordering, drawer behavior, single-status semantics, and backend persistence are unchanged. The numeric relevance score is still authoritative from the API. The new textual bands are display thresholds: HIGH 80–100, MEDIUM 50–79, LOW 0–49. No score recalculation, urgency inference, fabricated dates, or API changes were introduced.

## TEST_RESULTS

| Required command | Result |
| --- | --- |
| `npm --prefix frontend run lint` | Passed |
| `npm --prefix frontend run typecheck` | Passed |
| `npm --prefix frontend run build` | Passed; dashboard, management, and not-found routes generated |
| `npm --prefix frontend run test:integration` | **6 passed in 27.4s**, existing tests unchanged |
| `git diff --check` | Passed |

The browser suite verified server filters, client search, refresh, drawer/Escape/focus, durable status mutations after reload, oshi CRUD/stats, offline recovery, pagination, and no page overflow at 1440, 1200, 1024, and 768px. It used the existing disposable seeded database and Chrome configuration. Earlier in the same session, `oshi test` passed all **88 backend + 17 CLI tests**, frontend lint/typecheck, and the then-current six browser tests.

## MANUAL_VERIFICATION

Inspected the current running build before editing, then inspected real seeded cards in browser screenshots after editing. Additional browser-driven checks covered all ten records without changing personal data:

| Check | Result |
| --- | --- |
| Cards with deadlines | Actual API deadlines rendered with date/year, local time, and timezone; warm text outranks source metadata |
| Cards without deadlines/dates | No invented deadline, blank date section, or empty location row |
| Start/end/location | Present API fields rendered; narrow placement confirmed below the title |
| SAVED / INTERESTED / IGNORED | Exactly one current-status representation, inside the selected action |
| GOING | Visible beside the action buttons, no isolated far-right label |
| Wide/narrow layouts | Reviewed at 1440px and 768px; compact card content and no document overflow |
| Keyboard controls | Native keyboard type-ahead selected New, loaded three real matching updates, and retained visible focus |
| Drawer | Opened from the filtered feed and closed with Escape; no page errors |
| Mutations persist | The unchanged real-API browser suite verified Save/Going/Ignore after reload |

Review screenshots are local, ignored artifacts: [wide](../.runtime/ui-refinement/wide.png), [narrow](../.runtime/ui-refinement/narrow.png), [without dates](../.runtime/ui-refinement/without-dates.png), [ignored](../.runtime/ui-refinement/ignored.png), and [before](../.runtime/ui-refinement/before.png). Saved, Interested, and Going card captures are in the same directory. A read-only SQL dump comparison confirmed the personal database remained unchanged through both milestones.

## DEVIATIONS

No scope deviation. The supplied score-label examples did not define thresholds; 80 and 50 were chosen for display only. Native option menus remain native for accessibility; their closed controls use the refined styling. The drawer's existing layout was retained because this request did not require a drawer redesign.

## BLOCKERS

None for the UI refinement. For future Terminal sessions to resolve the installed `oshi` shorthand, the user still needs the installer-provided PATH line in `~/.zshrc`; shell startup files were intentionally not edited.

## NEXT

Both CLI-owned services are running and ready at `http://localhost:3000` and `http://localhost:8000` for review. Use `~/.local/bin/oshi hiraku` immediately, or apply `export PATH="$HOME/.local/bin:$PATH"` and use `oshi hiraku`. Use `oshi shuuryou` to stop them. Review these focused UI changes before any further product expansion.
