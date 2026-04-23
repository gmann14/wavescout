# WaveScout — Design Pass Findings (2026-04-23, revised)

Reviewed by: frontend-design review pass, revised after product-owner feedback.
Scope: all five top-level routes (Map, Atlas, Compare, Methodology, About), Spot/Section panels, satellite gallery, markdown content styling, and global chrome.

---

## 1. Honest Assessment

The current UI is already credible. It has solid route structure, sensible density, good accessibility habits, and a map/detail flow that matches the product. This is not a broken design in need of reinvention.

The problem is narrower: WaveScout still reads too much like a generic dark product shell and not enough like a distinctive coastal evidence tool. The previous pass over-corrected by treating NIR foam detection as the brand story. That is not stable enough. The stronger product truths, based on the current spec and methodology docs, are:

- **the map** as the main way users narrow the coastline
- **the satellite photos** as the most concrete evidence artifact in the product
- **explicit uncertainty** as part of the product's credibility

That should be the design center.

---

## 2. What's Genuinely Working (Preserve)

- **Information architecture.** The `Map`, `Atlas`, `Compare`, `How It Works`, and `About` route split is good. Keep it.
- **Color semantics.** Teal for confirmed/high-confidence references, orange for candidates, gray for context is already legible and reinforced in the map, legend, panels, and tests. Preserve those semantics.
- **Density calibration.** `SpotPanel` and `AtlasSectionPanel` fit a lot of information into a small area without feeling sloppy. Improve hierarchy, not density.
- **Map craft.** The current verified spot glow/dot/label treatment is the strongest piece of visual detailing in the app. Build around it.
- **Accessibility foundation.** Focus rings, modal semantics, keyboard shortcuts, and non-color legend cues already exist. Any redesign must preserve them.
- **Evidence language.** The current product docs consistently emphasize evidence, caveats, and uncertainty. The visual system should support that tone, not sensationalize it.

---

## 3. The Real Design Problems

### 3.1 Typography still signals "template app"

Using Geist Sans for both interface and display keeps the app clean, but it also keeps it generic. There is no typographic distinction between control chrome, editorial content, and evidence readouts.

**Impact:** HIGH.

### 3.2 First load does not explain the product fast enough

The home route opens on a map plus stats bar. That is useful once a user understands the taxonomy, but cold users need one orienting sentence before they read counts like `segments scored` and `high candidates`.

**Impact:** HIGH.

### 3.3 The most distinctive assets are under-promoted

The map is the primary navigation surface, and the satellite scenes are the primary evidence artifact. Both are central to the product, but only the map gets real prominence. The gallery is still too thumbnail-sized in `SpotPanel`, and `/compare` still opens like a uniform card grid instead of an evidence-first reading surface.

**Impact:** HIGH.

### 3.4 Panels are informative but not opinionated enough

`SpotPanel` currently treats the hero facts too evenly. `surf_potential_score`, `evidence confidence`, `scene count`, and summary copy all compete for attention at the same visual weight. The panel should answer the core questions faster without becoming louder.

**Impact:** MEDIUM.

### 3.5 Markdown/content pages undersell the quality of the writing

The methodology content is interesting, but the treatment is close to stock markdown. It needs a more editorial reading rhythm while staying restrained and technical.

**Impact:** MEDIUM.

### 3.6 Motion and polish are absent in the right places

The app does not need heavy animation, but a more deliberate arrival sequence and a few state transitions would help it feel authored. This is secondary to hierarchy and framing.

**Impact:** LOW-MEDIUM.

---

## 4. Direction To Commit To

**Internal concept: "Coastal Evidence Atlas."** Internal-only framing for the design team. Do **not** ship it as user-facing copy, a tagline, or marketing language. The user-facing framing remains what it already is: *surf discovery from space, by coastline and satellite evidence*, with the stronger one-liner pulled from `docs/PRODUCT-VISION.md`: *browse an unfamiliar coast, then inspect supporting imagery*.

Frame WaveScout, internally, as a modern coastal survey and evidence atlas, not as a dashboard and not as a speculative NIR-tech brand. The references should be:

- hydrographic and survey publications
- satellite-image annotation tools
- editorial science features with strong maps and quiet typography

This direction fits the actual product contract:

1. Users browse coastlines and candidate areas on a map.
2. Users inspect satellite scenes as evidence artifacts.
3. Users are repeatedly reminded what is known, inferred, and uncertain.

### What that means concretely

- **Map-first framing:** the home route gets a compact orientation block that explains what the user is looking at before the stats bar and legend do the rest.
- **Photo-first evidence surfaces:** `/compare` and the gallery become materially larger and easier to read, with acquisition/date/swell metadata treated as a survey readout.
- **Editorial typography with restraint:** one display serif for page titles and major section headers, a clean sans for UI, and mono for coordinates, dates, and evidence readouts.
- **Warm neutrals without semantic remapping:** warm the text and surface neutrals, but keep teal/orange/gray meaning intact.
- **Uncertainty visible in layout, not just copy:** caveats, confidence, and candidate status remain prominent and clearly separated from `surf potential score`.
- **NIR remains a tool, not a motif:** the NIR toggle can stay as a secondary analysis view, but it should not define the palette, logo, motion language, or hero moments.

---

## 5. Prioritized Recommendations

### Tier A — Highest leverage

1. **Adopt a stronger type system.**
   - Recommended default: **Source Serif 4** for display, **Geist Sans** for UI, **IBM Plex Mono** for technical readouts.
   - Rationale: Source Serif 4 (from Adobe, via Google Fonts, variable) has the editorial weight and optical sizes the project needs without the now-overused Newsreader/Instrument Serif signature. IBM Plex Mono reads distinctly more "technical instrument" than Geist Mono — the right match for a survey/hydrographic tone.
   - Fallback if you'd rather stay on one type foundry: **Newsreader** (display) + **Geist Sans** (UI) + **Geist Mono** (mono). Cheap to roll back to and still better than the current single-family setup.
   - **Scope rule:** serif is used only for page H1, route titles, and the single hero metric in `SpotPanel`. Everything else stays in Geist Sans or Plex Mono. Do **not** turn the app into a serif-heavy magazine layout.

2. **Add one orienting statement to the home route.**
   - Short copy above or beside the stats chip:
     `Browse Nova Scotia's coast by map, then inspect satellite evidence and confidence.`
   - The goal is comprehension, not a marketing hero.

3. **Promote imagery as a first-class evidence surface, and explicitly demote NIR/foam signals out of primary readouts.**
   - On `/compare`, lead with one large RGB scene per date block before the smaller grid continues.
   - In `SpotPanel`, increase thumbnail size when space allows and make metadata more scannable.
   - **NIR demotion, named explicitly:**
     - `web/src/components/CompareView.tsx` — the `RGB/NIR` toggle (currently in the primary filter bar at ~L322–331 and the lightbox at ~L449–461) moves off the primary bar and into a secondary/"detection details" affordance on the same page. RGB is the unconditional default.
     - `web/src/components/CompareView.tsx` — the per-thumbnail `%foam` badge (currently at ~L438–445) is removed from the grid and reappears only when a scene is opened with "detection details" expanded, or in the NIR mode view.
     - `web/src/components/MapView.tsx` — the `Foam: X/40` line in hover popups (currently at ~L280–289) is hidden by default; popups lead with score, rank, confidence, and direction.
     - `web/src/components/SpotPanel.tsx` — the `foamSummary` tile (currently at ~L202–217) is relabeled so "observations" and "satellite passes" no longer imply foam is the validated signal. Preferred wording: "Satellite passes analyzed" / "Scenes with detections" with a tooltip explaining the detection is exploratory.
   - Default emphasis on all three surfaces is RGB imagery + score + confidence. NIR and foam are available behind disclosure, but are not ambient.

4. **Rework `SpotPanel` hierarchy without sacrificing density or uncertainty parity.**
   - Make `surf potential score` the clear first numeric read.
   - **Hard rule:** `evidence confidence` stays on the same visual tier as the score — adjacent, explicitly labeled, and comparably weighted. Do **not** make the score a giant hero numeral that dominates confidence; that would regress the product's uncertainty contract (see `docs/SPEC.md` §confidence, and `docs/PRODUCT-VISION.md`).
   - Preserve highlights, caveats, verification status, and provenance signals.

5. **Improve map-adjacent typography and micro-chrome.**
   - Replace generic Mapbox popup HTML styling with a treatment that matches the app.
   - Tighten the stats bar and legend typography so the map page feels authored on first load.

### Tier B — Next pass

6. **Warm the neutrals.**
   - Shift primary text toward bone/off-white and secondary text toward warmer dim neutrals.
   - Keep the current teal/orange state system intact.

7. **Give content pages a more editorial reading rhythm.**
   - Better measures, better heading rhythm, section dividers, optional first-paragraph treatment.
   - Prioritize readability over ornament.

8. **Add restrained motion.**
   - Small stagger on map-page chrome.
   - Smooth bar and panel transitions where state changes are already meaningful.
   - Always respect `prefers-reduced-motion`.

### Tier C — Explicitly deferred (do not ship in this pass)

Tier C is intentionally empty in the active plan. Grain/noise textures, wordmark refinement, and route-level metadata chips were all considered and deferred — they are the classic drift bucket in design passes and will siphon review attention from the Tier A work. If the Tier A and B work ships cleanly, a fresh, scoped ticket can reopen any of these later with its own justification.

Specifically deferred and **not** to be re-added mid-flight:

- grain/noise surface texture
- persistent field rail or coordinate chips on every route
- wordmark redesign or logo work
- NIR false-color chrome shifts or mode theatrics
- decorative lat/lng readouts

---

## 6. Specific Corrections To The Previous Pass

- **Cut:** the idea that NIR/foam detection should be the visual signature of the brand.
- **Cut:** ember or false-color red replacing teal as the high-confidence/confirmed signal.
- **Cut:** a persistent left-side field rail across all routes.
- **Cut:** dramatic NIR-mode chrome shifts and other mode-based theatrics.
- **Keep, but revise:** gallery promotion. Make it photo-first and map-supported, not NIR-first.
- **Keep, but revise:** display typography. Use a quieter serif and apply it selectively.
- **Keep:** warm neutrals, improved hierarchy, better first-load framing, and subtle motion.

---

## 7. What I'm Not Recommending

- **Not a full rebrand or logo project.** Premature.
- **Not a semantic color-system rewrite.** Existing confirmed/candidate/context meanings are already working and already tested.
- **Not a persistent left rail.** Too much layout risk for too little value.
- **Not a map-style replacement.** The current dark basemap is acceptable.
- **Not heavy motion libraries.** CSS and existing transitions are enough.
- **Not building the brand around unvalidated detection claims.** The product earns trust by showing evidence and caveats, not by dramatizing one exploratory technique.

---

## 8. Implementation Priorities

If only four things ship from this pass, they should be:

1. better typography
2. clearer home-page framing
3. promoted imagery on compare/detail surfaces
4. improved panel hierarchy with uncertainty preserved

That sequence improves distinctiveness without undermining the current product contract.

---

## 9. Confidence

**High.** This revised direction is better aligned with:

- the product vision's emphasis on evidence and uncertainty
- the spec's confirmed/candidate/accessibility contracts
- the current app's strongest surfaces: the map and the satellite scenes

The companion implementation plan is at [DESIGN-PASS-2026-04-TDD.md](./DESIGN-PASS-2026-04-TDD.md).
