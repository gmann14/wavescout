# WaveScout — Design Pass Implementation Plan (Revised TDD, v2)

Companion to [DESIGN-PASS-2026-04.md](./DESIGN-PASS-2026-04.md).

**Change log from v1 (rolled in from reviewer critique, 2026-04-23):**

- Typography recommendation updated to **Source Serif 4 + Geist Sans + IBM Plex Mono**. Newsreader is retained as a one-step-rollback fallback.
- Stage 4 and Stage 5 now include **explicit NIR/foam demotion instructions** with file + line citations against current code, so "NIR stays secondary" becomes enforceable implementation work rather than aspirational doc language.
- Stage 4 now carries a **hard test** that NIR/foam is not the default emphasis on `/compare` first paint.
- Stage 5 now carries a **hard uncertainty-parity test**: `surf potential score` and `evidence confidence` must share visual tier.
- Stage 6 now includes the foam-line demotion in map popups (previously unscheduled).
- PR 3 (previously Stages 4+5 combined) is **split into PR 3a and PR 3b** so the two highest-risk product surfaces ship separately.
- Stage 9 (optional polish / grain / wordmark / coordinate chips) is **cut**. Any such work reopens as a fresh ticket post-ship.
- The `Coastal Evidence Atlas` concept is clarified as **internal-only**; not user-facing copy.

This revised plan assumes the **Coastal Evidence Atlas** direction:

- map and satellite photos are the primary design anchors
- uncertainty and evidence confidence remain explicit
- NIR remains a secondary analysis view, not a branding device
- tests protect product behavior and accessibility, not fragile CSS trivia

---

## Philosophy

Design implementation should add confidence where regressions are likely and avoid tests that only pin decorative details.

Use tests for:

- product semantics that must survive redesign
- accessibility and interaction behavior
- layout contracts that affect navigation or interpretation

Use manual review for:

- typography quality
- spacing and hierarchy craft
- subtle color tuning
- motion timing

Avoid tests that assert:

- exact hex values for every token
- exact animation names
- pseudo-element internals
- font-family string matching as the primary signal of success

---

## Stage 0 — Preserve current behavioral guardrails

**Goal:** keep the app's existing strengths intact before visual changes begin.

### Test work

- Keep existing route, legend, panel, and gallery tests.
- Add one focused e2e smoke test that checks:
  - `/` loads nav, legend, and stats area
  - confirmed spots and candidate segments remain distinguishable in nearby copy
  - the map token error and empty-data states still render when forced

### Why this stage exists

The current app already has meaningful coverage around non-color cues and detail panel behavior. Do not throw that away in favor of visual pinning tests.

---

## Stage 1 — Typography wiring

**Goal:** introduce Source Serif 4 (display) and IBM Plex Mono (technical readouts) alongside the existing Geist Sans, expose as CSS variables, without actually applying them to any surfaces yet. Pure wiring.

### Implementation

- In `web/src/app/layout.tsx`, import and load Source Serif 4 and IBM Plex Mono via `next/font/google`. Attach their `.variable` strings to the `<html>` element alongside the existing Geist variables.
- In `web/src/app/globals.css`, expose tokens:
  - `--font-display: var(--font-source-serif-4);`
  - `--font-sans: var(--font-geist-sans);`
  - `--font-mono: var(--font-ibm-plex-mono);`
- Add a single utility class `.font-display { font-family: var(--font-display), Georgia, serif; }` and `.font-readout { font-family: var(--font-mono), ui-monospace, monospace; }`.
- Do **not** apply the display or readout fonts to any existing component in this stage.

### Testing

- No dedicated new font-family assertion test. The reviewer was clear that these tests pin trivia without buying safety.
- Existing render tests (`Nav`, `CompareView`, `SpotPanel`, `ImageGallery`, `MapLegend`) must stay green.
- Manual check: page source shows the Source Serif 4 and Plex Mono stylesheets loaded via `next/font`; no FOUT visible on hard reload.

### Review checklist

- App still renders normally; no component uses the new fonts yet.
- No layout shift or font-loading issues.
- Serif and mono are available for later stages via CSS variables.
- Rollback path confirmed: swapping `Source_Serif_4` for `Newsreader` in `layout.tsx` is a one-line change that propagates everywhere downstream.

---

## Stage 2 — Warm neutrals without semantic color changes

**Goal:** improve surface and text tone while preserving the current teal/orange/gray meaning system.

### Implementation

- Add warm text/surface neutrals such as `bone` and `bone-dim`.
- Apply them to page copy, panels, and content surfaces.
- Leave verified/candidate/context semantics alone in map, legend, badges, and charts.

### Testing

- No token-level hex assertions.
- Rely on existing semantic tests, especially the legend and nav tests, to catch accidental meaning drift.

### Review checklist

- Confirmed/candidate/context cues still read the same.
- Contrast remains strong on dark surfaces.
- The app feels warmer, not rebranded.

---

## Stage 3 — Home-route framing and comprehension

**Goal:** explain the product faster on first load.

### Test (Red)

Add or extend an e2e test for `/` that expects:

- an orientation statement explaining map + satellite evidence
- the stats chip to remain present
- the legend to remain present on supported viewports

Example assertion target:

`Browse Nova Scotia's coast by map, then inspect satellite evidence and confidence.`

### Implementation (Green)

- Add a compact orientation block to the home route near the map chrome.
- Tighten the stats bar copy if needed so counts are easier to parse.

### Review checklist

- First-time users can understand the page before clicking anything.
- The map still dominates the route visually.
- This does not turn into a giant marketing hero.

---

## Stage 4 — Compare page: promote imagery AND demote NIR/foam

**Goal:** make `/compare` read like an evidence surface, not just a card grid, and explicitly move NIR/foam signals out of the primary reading path. This is the single highest-leverage stage of the pass — ship it alone (PR 3a below).

### Test (Red)

Extend `CompareView` tests in `web/src/components/__tests__/CompareView.test.tsx` to assert:

- a featured scene exists at the top of each comparison block (or at least the first block).
- the readout includes explicit same-date/acquisition context (date, swell, spot-count).
- sparse-date and missing-date states still work.
- **NIR/foam is not part of the default emphasis.** Specifically:
  - On initial render (no user interaction), the featured readout does **not** contain the strings `foam`, `%foam`, or `NIR`.
  - The primary filter bar does **not** contain the `RGB/NIR` toggle — that control moves to a secondary "detection details" area or the lightbox only.
  - The per-thumbnail `%foam` badge is not rendered in the grid by default.

Semantic hooks to introduce:

- `data-testid="compare-featured-scene"`
- `data-testid="compare-featured-readout"`
- `data-testid="compare-detection-details"` (collapsible; default-collapsed)

### Implementation (Green)

- Split the first scene of a date block into a larger featured module (RGB, not NIR).
- Keep the remaining scenes in a grid below, unchanged in density.
- Render the readout in Plex Mono with acquisition date, swell, direction, period, and spot count. No foam %, no NIR mention.
- **NIR/foam demotion, line-cited against current code:**
  - Move the `RGB/NIR` toggle (currently in the primary filter bar at `web/src/components/CompareView.tsx:322–331` and in the lightbox at `CompareView.tsx:449–461`) into a secondary "Detection details" disclosure. On first paint the disclosure is collapsed. Inside, expose the NIR toggle + any per-scene detection metadata.
  - Remove the per-thumbnail `%foam` badge (currently at `CompareView.tsx:438–445`) from the default grid render. It reappears only when "Detection details" is expanded or when NIR mode is active.
- Default emphasis on the page is: **date, RGB image, swell, direction, spot count, confidence**. Foam/NIR is a power-user affordance.

### Review checklist

- `/compare` feels image-led within one screen.
- Same-date comparison remains explicit.
- Missing imagery and sparse states are still clear.
- A first-time user cannot see any foam percentage or NIR label without clicking "Detection details".
- Power users can still reach NIR + foam in two clicks.

---

## Stage 5 — SpotPanel hierarchy refinement AND foam-label demotion

**Goal:** help the panel answer its four core questions faster without dropping caveats, density, or uncertainty parity. Ship this alone (PR 3b below).

### Test (Red)

Extend `web/src/components/__tests__/SpotPanel.test.tsx` to assert:

- `surf potential score` is labeled and present.
- `evidence confidence` is labeled and present.
- confirmed/candidate verification status remains visible.
- caveats still render when present.
- **Uncertainty-parity hard rule:** `surf potential score` and `evidence confidence` render at the same visual tier. Specifically, the bounding box of the confidence label+value has a height within ±20% of the score's bounding box, and the confidence element is not visually hidden, collapsed, or moved below the fold on mobile. (Use `getBoundingClientRect` or computed font-size/line-height to assert — whichever is least fragile in jsdom. If jsdom can't measure, lift this into an e2e Playwright test.)
- **Foam-label demotion:** the `foamSummary` tile (currently at `web/src/components/SpotPanel.tsx:202–217`) no longer labels its metrics as `observations` in a way that implies foam is the validated signal. The tile label is one of: `Satellite passes analyzed`, `Scenes with detections`, or an equivalent wording that does not present foam count as a hero fact.

### Implementation (Green)

- Rework the top section of `SpotPanel` so the score is visually first but not overpowering.
- `surf potential score` and `evidence confidence` share a tier — same row, comparable size, comparable weight. The existing 3-up grid is acceptable; a score-then-confidence pair with equal emphasis is also acceptable. A giant hero numeral for the score alone is **not** acceptable.
- Relabel the `foamSummary` block:
  - "observations" → "scenes with detections"
  - "satellite passes" → "satellite passes analyzed"
  - Add a small tooltip or footnote: *"Detections are exploratory. A high count suggests recurring activity, not confirmed surf."*
- Keep highlights, caveats, verification status, gallery, swell profile, and provenance visible.
- Avoid giant hero numerals that crowd the panel on mobile (≤375px width).

### Review checklist

- The score reads first.
- Confidence is unmissable and visually peer with the score.
- Foam/NIR-derived numbers no longer read as hero facts.
- Density remains strong on both mobile and desktop.
- Caveats are still visible above the fold on desktop and within one scroll on mobile.

---

## Stage 6 — Map chrome and popup polish, with foam-line demotion

**Goal:** make the map route feel more intentional without disrupting interaction, and bring the map popup in line with the NIR/foam demotion decided in Stage 4.

### Test work

- Keep the existing legend test that checks non-color cues.
- Add a lightweight test asserting that the default hover-popup HTML for a `segments-high` feature **does not** contain the substring `Foam:` unless a "detection details" affordance is invoked. Prefer an e2e Playwright test that hovers a known-high segment and reads the popup DOM — jsdom will not render Mapbox.
- Do not add tests that depend on exact popup HTML structure beyond that semantic assertion.

### Implementation

- Improve stats bar typography and spacing.
- Restyle popups so they match the app's voice (Plex Mono for numbers, Geist Sans for the spot/segment id, Source Serif 4 nowhere).
- **Foam-line demotion:** in `web/src/components/MapView.tsx`, the `Foam: X/40` line (currently at L280–289) and the `Profile:` line are removed from the default popup. Popups default to: segment id, score, confidence, rank, primary direction. Foam and profile components may be added later behind a URL flag or a user preference, but not in this pass.
- Optionally add small metadata readouts in existing map chrome (acquisition date, dataset provenance). No persistent field rail (explicitly deferred).

### Review checklist

- The map still feels dominant.
- Popups are easier to read and no longer present foam as a peer metric to score.
- No Mapbox interaction regressions (hover in, hover out, click, mobile tap).

---

## Stage 7 — Methodology and content-page polish

**Goal:** make `/methodology` feel as strong as the writing.

### Testing

- No dedicated new test required unless the component structure changes materially.
- Existing page render coverage should remain green.

### Implementation

- Improve heading rhythm and spacing in `MarkdownContent.tsx`.
- Use the display serif selectively for major headings.
- Consider section dividers, better measure, and optional first-paragraph styling.

### Review checklist

- The page reads like a technical field note, not generic markdown.
- Links, code, tables, and lists remain legible.
- No accessibility regressions from heading or contrast changes.

---

## Stage 8 — Motion and reduced-motion polish

**Goal:** add a small amount of authored motion where it improves orientation.

### Testing

- Add one reduced-motion smoke test only if motion is applied to critical entrance states or controls.
- Do not assert exact animation names or durations in automated tests.

### Implementation

- Add subtle entrance motion to home-route chrome.
- Add smooth width/opacity transitions where state changes already exist.
- Respect `prefers-reduced-motion`.

### Review checklist

- Motion helps orientation rather than calling attention to itself.
- Reduced-motion behavior is verified manually in macOS settings.

---

## Stage 9 — Cut

**This stage was removed during review.**

The previous draft scheduled optional polish work here (grain/noise, coordinate chips, wordmark tweaks). Experience says this bucket always absorbs review attention away from the Tier A stages — and the reviewer called it out explicitly. If any of that work becomes worthwhile after Stages 1–8 ship, open a fresh, scoped ticket with its own justification. Do **not** slip it into this pass.

The stage is kept here as a placeholder only so Stage 10 keeps its number and downstream references stay stable.

---

## Stage 10 — Final review and evidence capture

After implementation:

1. Capture screenshots of all routes at desktop and mobile widths.
2. Verify:
   - confirmed/candidate/context meaning still reads correctly
   - map interactions still work with panels open
   - compare states still handle sparse or missing data correctly
   - content pages remain readable
3. Run the full suite:
   - `pnpm test`
   - `pnpm test:e2e`
4. Update the findings doc with an implementation note and screenshot references if desired.

---

## Suggested PR Boundaries

Use small PRs with reviewable scope. The Stage 4+5 work is explicitly split — they are the two highest-risk product surfaces, and they should land in separate PRs so either can be reverted without the other:

1. **PR 1:** Stages 1–2
   - typography wiring (Source Serif 4, Geist, Plex Mono variables)
   - warm neutrals (bone / bone-dim tokens applied to body copy and surfaces)

2. **PR 2:** Stage 3
   - home-route framing (orienting statement)

3. **PR 3a:** Stage 4
   - compare imagery promotion
   - NIR/foam demotion on `/compare`

4. **PR 3b:** Stage 5
   - SpotPanel hierarchy refinement
   - foam-label demotion in `foamSummary`

5. **PR 4:** Stage 6
   - map chrome + popup polish
   - foam-line demotion in map popups

6. **PR 5:** Stages 7–8
   - methodology/content polish
   - motion and reduced-motion polish

7. **PR 6:** Stage 10
   - screenshot pass, final verification, implementation note in the findings doc

Stage 9 is cut; it does not ship.

This keeps the high-risk visual shifts grouped with the tests that matter, and gives each product surface its own reviewable boundary.

---

## Risks And Mitigations

- **Semantic color drift.**
  - Mitigation: preserve teal/orange/gray mapping and keep legend tests intact.

- **Typography making the app feel too editorial or too precious.**
  - Mitigation: keep serif usage selective and review the map route first.

- **Featured imagery hurting compare density.**
  - Mitigation: feature only one scene per block and keep the grid immediately below.

- **SpotPanel hierarchy accidentally hiding caveats.**
  - Mitigation: add tests that keep `surf potential score`, `evidence confidence`, and caveats explicit.

- **Motion or polish work absorbing too much time.**
  - Mitigation: stage it late and make it easy to cut.

---

## Out Of Scope

- full logo/identity redesign
- persistent field rail
- NIR-mode dramatization
- semantic recoloring of verified/candidate states
- map-style replacement
- heavy motion library adoption
- grain/noise surface texture
- coordinate chips, route-level metadata readouts outside of existing headers
- any new foam-derived UI language (no new "foam %" badges, no new observation counters)

---

## Success Criteria

The redesign is successful if:

- the home page explains itself faster
- the map and photos feel like the product's core surfaces
- uncertainty remains visible instead of being designed away
- the app looks more authored without losing clarity, density, or accessibility
- a first-time user cannot see any foam percentage or NIR label on `/compare` without invoking "Detection details"
- on `/spot` panels, `surf potential score` and `evidence confidence` read as peer facts, not as headline vs. footnote

---

## Ready-state declaration

This plan is **ready to implement**. Every stage has:

- a clear goal
- an explicit test or manual review step
- named file+line citations for demotion work where applicable
- a review checklist
- a defined PR boundary
- a rollback path for typography and color tokens

No known ambiguities remain in the docs. If a new ambiguity surfaces mid-implementation, resolve it in the docs before writing the code — do not let the plan drift.
