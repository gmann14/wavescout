# WaveScout Non-Manual Implementation Specs

*Updated: 2026-05-25*  
*Status: Ready-for-handoff specs for implementation agents*

## Purpose

This document converts the current non-manual follow-up work into implementation-ready tickets. These are scoped so another agent can pick them up without needing Graham's visual review or private local knowledge.

Use this with:

- [tasks.md](../tasks.md)
- [ROADMAP.md](ROADMAP.md)
- [IMPLEMENTATION-BACKLOG.md](IMPLEMENTATION-BACKLOG.md)
- [DATA-CONTRACTS.md](DATA-CONTRACTS.md)
- [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md)
- [PUBLIC-OUTPUT-POLICY.md](PUBLIC-OUTPUT-POLICY.md)
- [CODEX-CLOUD-SETUP.md](CODEX-CLOUD-SETUP.md)

## Global Rules

- Root `tasks.md` is the canonical task source.
- Keep public task entries free of private spot notes, credentials, unpublished customer/user context, and exact sensitive observations.
- Do not edit `.claude/tasks.md` as the source of truth; use it only as historical context.
- Prefer tests that verify behavior, command safety, and data contracts over snapshotting generated payloads.
- Do not run long Earth Engine or Overpass jobs unless the ticket explicitly calls for them.
- If a command regenerates committed artifacts, inspect the diff before deciding whether it belongs in the PR.
- Commit task-file updates with the implementation/docs change that changes task status.

## Suggested PR Order

1. `NM-01` release-readiness reproducibility
2. `NM-02` canonical task/backlog reconciliation
3. `NM-03` gallery asset URL abstraction
4. `NM-04` bathymetry fixture hardening
5. `NM-05` swell-line review tooling

`NM-01` and `NM-02` can run in parallel if the agents coordinate on `tasks.md`. `NM-03`, `NM-04`, and `NM-05` have disjoint write scopes and can run in parallel after the repo status is clean.

## Definition Of Ready

A ticket is ready when:

- the target files listed in the ticket exist in the current checkout
- the agent has checked `git status --short --branch`
- any local uncommitted user changes are either unrelated or explicitly accounted for
- the acceptance criteria are copied into the PR description or handoff

## Definition Of Done

A ticket is done when:

- red tests were added first or the ticket explains why a docs-only validation is the red step
- green implementation is complete
- relevant docs and `tasks.md` are updated
- verification commands listed in the ticket pass, or failures are documented with exact command output
- no generated or unrelated artifacts are left dirty

---

## `NM-01` Release-Readiness Reproducibility

Priority:

- P0

Owner fit:

- implementation agent

Problem:

- `python3 pipeline/scripts/check_release_readiness.py` currently depends on the invoking interpreter and runs all rebuild/test commands inline.
- A local run on 2026-05-25 failed under Homebrew Python 3.14 because `pipeline.research.swell_lines_v4.detect` could not import `pywt`.
- `requirements.txt` already includes `PyWavelets`, and CI installs requirements under Python 3.12. The intended runtime and local setup path need to be unambiguous.
- Full readiness can also regenerate committed public artifacts before failing, which makes debugging noisier.

Goal:

- Make the documented release-readiness path reproducible from a clean checkout.
- Make failures easier to diagnose without leaving unrelated generated diffs.
- Keep CI behavior aligned with the documented local behavior.

Non-goals:

- Do not change the release checklist criteria.
- Do not weaken swell-line tests to hide missing dependencies.
- Do not remove `PyWavelets` or skip V4 research tests just because the local environment is incomplete.

Likely files:

- `pipeline/scripts/check_release_readiness.py`
- `pipeline/scripts/_release_checks.py`
- `requirements.txt`
- `docs/CODEX-CLOUD-SETUP.md`
- `README.md`
- `docs/RELEASE-CHECKLIST.md`
- `tests/pipeline/test_release_checks.py`
- new `tests/pipeline/test_release_readiness_command_plan.py`
- optional helper under `pipeline/scripts/` if a small bootstrap/check script is warranted

### Red

Add focused failing tests before implementation:

- `tests/pipeline/test_release_readiness_command_plan.py`
  - Extract or require a `build_command_plan(...)` function from `check_release_readiness.py`.
  - Assert the default command plan includes:
    - `build_web_data.py`
    - `build_atlas_web_data.py`
    - `validate_public_dataset.py --strict --require-atlas`
    - `python -m pytest`
    - `pnpm test`
    - `pnpm exec tsc --noEmit`
    - `pnpm build`
  - Assert `--include-e2e` appends `pnpm test:e2e`.
  - Assert the Python executable used in Python commands is injectable for tests, not hardcoded to one developer's interpreter path.
- Add or extend a dependency smoke test:
  - `import pywt` must succeed in the intended test environment because `test_swell_line_detection_v4.py` imports V4 detection code at collection time.
  - If this goes into a new `tests/pipeline/test_dependency_imports.py`, keep it small and limited to dependencies that are required for checked-in tests.
- Add a docs consistency check if the repo already has a suitable pattern, or add a simple assertion in a pipeline test:
  - `README.md`, `docs/CODEX-CLOUD-SETUP.md`, and `docs/RELEASE-CHECKLIST.md` must name the same supported Python major/minor for release checks.

Manual red command to capture before fixing:

```bash
python3 -m pytest tests/pipeline/test_swell_line_detection_v4.py
```

Expected failure in the broken local environment:

- `ModuleNotFoundError: No module named 'pywt'`

### Green

Implement the minimum reliable path:

- Refactor `check_release_readiness.py` so command construction is testable:
  - command plan is built in a pure helper
  - command execution stays separate
  - report writing behavior remains unchanged
- Document one supported local runtime:
  - Prefer Python 3.12 if matching CI is simplest.
  - If Python 3.14 is intended to work too, verify all required packages install and import there before documenting it.
- Update setup docs with exact commands:

```bash
python3.12 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
python pipeline/scripts/check_release_readiness.py --skip-commands
```

- Clarify the difference between:
  - artifact-only gate: `python pipeline/scripts/check_release_readiness.py --skip-commands`
  - full local gate: `python pipeline/scripts/check_release_readiness.py`
  - browser-inclusive gate: `python pipeline/scripts/check_release_readiness.py --include-e2e`
- If full local gate still regenerates data by design, explicitly document that it may modify generated artifacts and must be run from a clean worktree.
- If practical, add a `--no-rebuild` or `--artifact-only` alias only if it reduces ambiguity without duplicating existing `--skip-commands`.

### Refactor

- Keep output report structure backward-compatible.
- Avoid introducing a custom task runner unless it replaces meaningful duplication.
- Keep CI on Python 3.12 unless there is a concrete reason to move it.
- Keep dependency checks near tests; do not add runtime imports to production scripts just to test dependencies.

### Acceptance Criteria

- `python -m pytest tests/pipeline/test_swell_line_detection_v4.py` passes in the documented environment.
- `python -m pytest tests/pipeline/test_release_checks.py tests/pipeline/test_release_readiness_command_plan.py` passes.
- `python pipeline/scripts/check_release_readiness.py --skip-commands` passes from a clean checkout.
- The docs all point to the same supported Python runtime.
- A failed full readiness run writes a report but does not obscure the root failing command.
- `git status --short` after verification contains only intentional changes.

### Verification Commands

```bash
python -m pytest tests/pipeline/test_release_checks.py tests/pipeline/test_swell_line_detection_v4.py
python pipeline/scripts/check_release_readiness.py --skip-commands
cd web && pnpm test && pnpm exec tsc --noEmit
```

### Handoff Notes

Record:

- Python executable and version used
- whether the full non-skip readiness command was run
- whether any generated artifact diffs were intentionally committed

---

## `NM-02` Canonical Task And Backlog Reconciliation

Priority:

- P0

Owner fit:

- implementation or docs agent

Problem:

- Root `tasks.md` still lists "Ship the Hamburg worktree to `main`" as active even though `main` is at `99930d1 Merge Hamburg research and gallery guardrails`.
- `.claude/tasks.md` and older roadmap/backlog files contain useful historical detail but no longer match the current repo exactly.
- Agents need a public-safe, current task board that does not send them into already-merged work.

Goal:

- Make root `tasks.md` accurately reflect the current active work.
- Preserve useful old backlog material by translating it into current public-safe tasks or marking it historical/deferred.
- Make it obvious which future tasks are non-manual and which require Graham's review.

Non-goals:

- Do not delete historical `.claude` specs unless explicitly requested.
- Do not add private spot notes to public docs.
- Do not re-open shipped WS tickets just because old docs mention them.

Likely files:

- `tasks.md`
- `docs/IMPLEMENTATION-BACKLOG.md`
- `docs/ROADMAP.md`
- `docs/IMPLEMENTATION-KICKOFF.md`
- optionally `CURRENT.md` if it is intentionally being adopted into the repo

### Red

This is primarily docs/task hygiene, but still use checks:

- Add a small public-task consistency test if the repo accepts doc tests:
  - `tests/pipeline/test_task_source_consistency.py`
  - assert root `tasks.md` exists
  - assert root `tasks.md` does not list the exact stale active phrase `Ship the Hamburg worktree`
  - assert `tasks.md` mentions this non-manual spec doc while these tasks are active
- If adding a test feels too brittle, the red step is a documented failing review note:
  - quote the stale active item
  - quote the merge commit showing the work is already on `main`
  - include this in the PR description before editing

### Green

Update public task truth:

- Move or rewrite stale Hamburg task:
  - If truly complete, move it to `Done` with commit reference `99930d1`.
  - If follow-up remains, name the follow-up precisely, such as "Verify Hamburg-generated gallery artifacts remain reproducible in the documented environment."
- Add non-manual active tasks corresponding to this document:
  - release-readiness reproducibility
  - task/backlog reconciliation
  - gallery asset URL abstraction
  - bathymetry fixture hardening
  - swell-line review tooling
- Keep the manual V5 scene review separate and explicitly marked as requiring Graham or a human visual reviewer.
- Update `docs/IMPLEMENTATION-BACKLOG.md` to clarify:
  - WS-01 through WS-09 are largely implemented as of the current release gate work
  - future work should start from `tasks.md` and this non-manual spec
  - older WS tickets remain historical unless reactivated with a new task ID
- Update `docs/IMPLEMENTATION-KICKOFF.md` if it still points new agents to obsolete first steps.

### Refactor

- Use concise task titles that can become branch names.
- Avoid duplicating full specs in `tasks.md`; link this document instead.
- Keep "manual review" and "implementation agent" work clearly separated.

### Acceptance Criteria

- `tasks.md` no longer tells agents to ship already-merged Hamburg work.
- `tasks.md` lists current non-manual implementation work with links or ticket IDs.
- Historical backlog docs clearly say when they are historical versus current.
- No private local knowledge or sensitive spot notes were added.
- Any added test passes.

### Verification Commands

```bash
python -m pytest tests/pipeline/test_task_source_consistency.py
rg -n "Ship the Hamburg worktree|source of truth|NM-" tasks.md docs
```

If no test is added, replace the first command with:

```bash
git diff -- tasks.md docs/IMPLEMENTATION-BACKLOG.md docs/IMPLEMENTATION-KICKOFF.md
```

### Handoff Notes

Record:

- which old active tasks were closed as stale
- which tasks remain manual-only
- any old backlog items intentionally left historical

---

## `NM-03` Gallery Asset URL Abstraction

Priority:

- P1

Owner fit:

- implementation agent

Problem:

- Root `tasks.md` asks for a long-term gallery hosting decision before public launch.
- Current web data assumes web-root-relative image paths served from `web/public/gallery/` and `web/public/atlas-gallery/`.
- The deployment spec recommends static-hosted images for initial launch and Cloudflare R2/CDN after atlas/image volume grows.
- The pipeline and validators should support that decision intentionally rather than baking in one path forever.

Goal:

- Keep local/static gallery paths working by default.
- Add a deliberate, tested path for CDN-prefixed image URLs in generated manifests.
- Keep local asset validation strict for local paths while not falsely failing remote CDN URLs.
- Document when to use static hosting versus CDN/R2.

Non-goals:

- Do not create Cloudflare accounts, buckets, tokens, or secrets.
- Do not upload real images to R2.
- Do not rewrite image-generation logic.
- Do not weaken local missing-file validation for web-root-relative paths.

Likely files:

- `pipeline/scripts/build_web_data.py`
- `pipeline/scripts/build_atlas_web_data.py`
- `pipeline/scripts/_public_dataset.py`
- `web/scripts/validate-gallery-assets.mjs`
- `docs/DATA-CONTRACTS.md`
- `DEPLOY.md`
- `docs/RELEASE-CHECKLIST.md`
- `tests/pipeline/test_gallery_manifest_schema.py`
- `tests/pipeline/test_release_checks.py`
- new or extended web script tests if the repo has a Node test pattern

### Red

Add tests that fail against the current local-only assumption:

- Pipeline manifest path tests:
  - Given a gallery scene with `rgb_path: "/gallery/foo/bar.png"`, generation preserves the local path by default.
  - Given an environment variable such as `WAVESCOUT_GALLERY_URL_PREFIX=https://cdn.example.test/gallery`, generation emits `https://cdn.example.test/gallery/foo/bar.png`.
  - Prefix normalization avoids double slashes.
  - Null image paths remain null.
- Dataset validation tests:
  - web-root-relative paths must resolve under `web/public/`
  - remote `https://` image URLs are allowed only when a CDN mode/config is explicitly present in `dataset-manifest.json`
  - unsupported schemes such as `file:`, `javascript:`, and protocol-relative `//cdn...` fail
- Web asset validator tests:
  - local paths are checked on disk
  - remote HTTPS URLs are counted and skipped with an explicit message
  - mixed local and remote manifests behave deterministically

Suggested test names:

- `tests/pipeline/test_gallery_url_prefix.py`
- `tests/pipeline/test_public_dataset_remote_assets.py`
- `web/scripts/validate-gallery-assets.test.mjs` if introducing Node's built-in test runner is acceptable

### Green

Implement the smallest abstraction:

- Add a helper such as:

```python
def public_gallery_url(path: str | None, *, prefix: str | None) -> str | None:
    ...
```

- Default behavior:
  - no prefix means emit existing web-root-relative paths
  - validator checks local files exactly as today
- CDN behavior:
  - prefix must be absolute HTTPS
  - generated paths keep the same relative suffix after `/gallery/` or `/atlas-gallery/`
  - `dataset-manifest.json` records image delivery mode, for example:

```json
{
  "image_delivery": {
    "mode": "static-public",
    "gallery_url_prefix": null
  }
}
```

or:

```json
{
  "image_delivery": {
    "mode": "cdn",
    "gallery_url_prefix": "https://cdn.example.test/gallery"
  }
}
```

- Update `validate-gallery-assets.mjs`:
  - local web-root-relative paths still must exist
  - HTTPS URLs are valid only if manifest metadata says CDN mode
  - remote URLs are not fetched during build
- Update release checks so CDN mode does not require local files for remote URLs, but still validates URL shape and manifest consistency.

### Refactor

- Centralize image path/url handling instead of duplicating string prefix logic in multiple builders.
- Keep atlas and spot gallery behavior symmetrical.
- Keep default static-hosting behavior unchanged so current release data does not churn.
- Do not add Cloudflare-specific code to generic manifest generation; deployment docs can describe R2.

### Acceptance Criteria

- Existing local manifests still validate and build.
- CDN-prefix generation is covered by tests.
- Local missing image paths still fail.
- Remote HTTP(S) behavior is explicit:
  - `https://` allowed only in CDN mode
  - `http://` rejected unless a test-only exception is explicitly scoped
  - unsafe schemes rejected
- `DEPLOY.md` states the current decision:
  - keep `web/public/gallery/` in the artifact for initial launch
  - move to R2/CDN when atlas coverage or traffic exceeds the documented threshold
- `docs/DATA-CONTRACTS.md` describes both local and CDN image path contracts.

### Verification Commands

```bash
python -m pytest tests/pipeline/test_gallery_manifest_schema.py tests/pipeline/test_release_checks.py tests/pipeline/test_gallery_url_prefix.py
cd web && pnpm validate:assets && pnpm build
```

If a Node validator test is added:

```bash
cd web && node --test scripts/validate-gallery-assets.test.mjs
```

### Handoff Notes

Record:

- chosen environment variable name
- whether current committed data stays local or is regenerated
- whether remote URL mode was tested only with fixtures or real generated manifests

---

## `NM-04` Bathymetry Fixture Hardening

Priority:

- P1

Owner fit:

- implementation agent with geospatial comfort

Problem:

- `pipeline/scripts/11_score_geometry.py` includes a GEBCO bathymetry hook and `score_bathymetry(...)`, but generated public data still reports `0.0` bathymetry scores because no real GEBCO file is present.
- The current bathymetry sampling is only lightly protected by tests.
- Agents can improve the implementation and tests without downloading full GEBCO or making product claims.

Goal:

- Make bathymetry scoring deterministic and testable with small fixtures.
- Preserve graceful behavior when no bathymetry file exists.
- Prepare the code for a real GEBCO subset without requiring it in CI.

Non-goals:

- Do not commit a large NetCDF.
- Do not change ranking weights based on unreviewed bathymetry results.
- Do not claim surf quality improvement from bathymetry until a real-data calibration pass is run.

Likely files:

- `pipeline/scripts/11_score_geometry.py`
- `tests/pipeline/test_geometry_support.py`
- new `tests/pipeline/test_bathymetry_scoring.py`
- `docs/CODEX-CLOUD-SETUP.md`
- `.claude/SPEC-bathymetry-integration.md` as historical implementation guidance
- optional new helper module `pipeline/scripts/_bathymetry.py`

### Red

Add fixture-backed tests:

- Missing dataset:
  - `score_bathymetry(lon, lat, None)` returns `0.0` and an explanation containing `not available`.
- Synthetic GEBCO-like object:
  - Create an in-memory fake object with `variables["lat"]`, `variables["lon"]`, and `variables["elevation"]`.
  - Ensure underwater negative elevations are converted to positive depths.
  - Ensure a stronger offshore depth gradient scores higher than a flat/shallow shelf.
  - Ensure out-of-range or malformed variables return a controlled `0.0` with a lookup-failed explanation.
- Directional sampling:
  - Current implementation samples by latitude offset only. Add a red test requiring sampling along the segment's seaward orientation, or explicitly document that orientation-aware sampling is deferred.
  - Preferred target: refactor scoring to accept an offshore bearing so a south-facing segment samples southward, not always north/south by array index accident.
- Loader path:
  - `try_load_gebco()` should look in the documented path and return `None` cleanly when `netCDF4` is absent or the file is missing.

Suggested tests:

- `test_missing_bathymetry_returns_zero`
- `test_synthetic_steep_gradient_scores_above_flat_shelf`
- `test_bathymetry_lookup_failure_is_controlled`
- `test_bathymetry_sampling_uses_offshore_bearing`

### Green

Implement in small steps:

- Move bathymetry helpers into `_bathymetry.py` if that makes tests cleaner.
- Add an explicit scoring helper:

```python
def sample_bathymetry_transect(
    gebco_ds: object,
    lon: float,
    lat: float,
    offshore_bearing_deg: float,
    distances_m: list[float],
) -> list[float | None]:
    ...
```

- Use existing `pyproj` transformers to convert sample distances from meters to WGS84 coordinates.
- Score from sampled depths:
  - no valid underwater depths: `0.0`
  - shallow/flat shelf: low score
  - moderate depth increase over 1000m: medium score
  - steep but plausible nearshore gradient: high score capped at 20
- Keep `score_bathymetry(...)` backward-compatible or update call sites/tests together.
- In `main()`, pass the segment orientation/offshore bearing into bathymetry scoring.
- Keep no-file behavior unchanged: no GEBCO means all bathymetry scores are zero with caveats.

### Refactor

- Separate sampling from scoring:
  - sampling handles coordinate lookup and missing values
  - scoring handles depth-gradient heuristics
- Use small named constants for distances and gradient thresholds.
- Avoid broad bare `except`; catch expected lookup/import/value errors where practical.
- Add explanations that are clear in public payloads and methodology:
  - `Bathymetry data not available`
  - `Nearshore depth gradient appears gradual`
  - `Nearshore depth gradient appears steep`

### Acceptance Criteria

- Bathymetry tests pass without real GEBCO.
- `python pipeline/scripts/11_score_geometry.py` still works without GEBCO and does not require network unless `--allow-road-download` is used.
- Existing geometry/coastal context tests still pass.
- Docs state the expected local GEBCO path and that CI uses synthetic fixtures only.
- Public generated data remains truthful if bathymetry is unavailable.

### Verification Commands

```bash
python -m pytest tests/pipeline/test_geometry_support.py tests/pipeline/test_bathymetry_scoring.py
python pipeline/scripts/11_score_geometry.py
python pipeline/scripts/build_web_data.py
python pipeline/scripts/validate_public_dataset.py --strict --require-atlas
```

Only run the full scoring script if the worktree has the expected coastline data and the agent is prepared to inspect generated diffs.

### Handoff Notes

Record:

- whether real GEBCO was used or only fixtures
- whether any generated coastline/web data was regenerated
- any ranking changes observed if real GEBCO was tested locally

---

## `NM-05` Swell-Line Review Tooling

Priority:

- P2

Owner fit:

- implementation agent

Problem:

- V5 swell-line research is waiting on manual labels in `pipeline/research/swell_lines_v5/scene_reviews.csv`.
- The label decisions are manual, but the review workflow can be made faster and less error-prone.
- A static local review sheet/contact sheet can be generated without needing Graham's judgment.

Goal:

- Generate a browser-friendly review artifact from `scene_reviews.csv`.
- Show RGB/NIR pairs, metadata, and label definitions.
- Make it easy to copy labels back into CSV or generate an updated CSV from a simple local form.

Non-goals:

- Do not auto-label scenes.
- Do not change the scientific decision criteria.
- Do not add a server or database.
- Do not publish review images publicly.

Likely files:

- `pipeline/research/swell_lines_v5/scene_reviews.csv`
- `pipeline/research/swell_lines_v5/REVIEW_INSTRUCTIONS.md`
- `pipeline/research/swell_lines_v5/summarize_reviews.py`
- new `pipeline/research/swell_lines_v5/build_review_sheet.py`
- new `pipeline/research/swell_lines_v5/review_sheet.html` if generated output is intentionally committed, otherwise document it as generated/untracked
- `tests/pipeline/test_swell_line_review_sheet.py`

### Red

Add tests for a pure renderer/helper before building HTML:

- Given a small CSV fixture with two rows, `load_review_rows(...)` returns:
  - review id
  - spot slug/name
  - date
  - source
  - RGB/NIR paths
  - current label/note
- `render_review_sheet(...)` emits:
  - one card per row
  - both RGB and NIR image references when present
  - label definitions for `clear_positive`, `ambiguous`, `clear_negative`
  - frozen organized rows marked distinctly
  - CSV-safe output instructions
- Missing image paths are reported in a warnings list but do not crash rendering.
- The renderer escapes notes and labels so CSV content cannot inject arbitrary HTML.

Suggested tests:

- `tests/pipeline/test_swell_line_review_sheet.py`
- Use `tmp_path` with tiny fake image files or just path existence checks depending on implementation.

### Green

Implement a static generator:

```bash
python pipeline/research/swell_lines_v5/build_review_sheet.py
```

Expected behavior:

- Reads `scene_reviews.csv`.
- Writes `pipeline/research/swell_lines_v5/review_sheet.html` or a user-specified `--out`.
- Uses relative image paths so the HTML works when opened from the repo checkout.
- Groups rows by spot.
- Puts frozen organized scenes first within each group.
- Displays:
  - spot name
  - date
  - source
  - current label/note
  - RGB image
  - NIR image
  - optional annotated image links if available
- Includes a compact instruction block copied from `REVIEW_INSTRUCTIONS.md`.
- Optional but useful:
  - embed a small `<textarea>` block with one CSV-ready line per scene for user-entered labels
  - add keyboard-free radio buttons that update a "copy this CSV patch" text area client-side

### Refactor

- Keep data loading, HTML rendering, and CLI argument parsing separate.
- Use only Python standard library unless a dependency already exists.
- Do not commit generated HTML unless the team wants review artifacts tracked. If committed, add a note explaining it is derived from the CSV.
- If generated HTML is untracked, add it to `.gitignore` only if that matches repo conventions.

### Acceptance Criteria

- Review sheet can be generated from a clean checkout.
- HTML opens locally and displays all rows from `scene_reviews.csv`.
- Missing images are reported clearly.
- Existing summarizer still works:

```bash
python pipeline/research/swell_lines_v5/summarize_reviews.py
```

- No labels are changed by the generator.
- Tests cover escaping and row rendering.

### Verification Commands

```bash
python -m pytest tests/pipeline/test_swell_line_review_sheet.py
python pipeline/research/swell_lines_v5/build_review_sheet.py --out /tmp/wavescout-swell-line-review.html
python pipeline/research/swell_lines_v5/summarize_reviews.py
```

If `summarize_reviews.py` modifies `summary.json`, inspect whether that belongs in the PR.

### Handoff Notes

Record:

- output path used
- whether generated HTML is committed or intentionally untracked
- any missing image warnings

---

## Parallel Agent Assignment Template

Use this prompt when handing one ticket to another implementation agent:

```text
Work in /Users/grahammann/Coding/wavescout.
Read AGENTS.md, root tasks.md, and docs/NON-MANUAL-IMPLEMENTATION-SPECS.md.
Implement ticket NM-XX only.
Follow the Red/Green/Refactor plan exactly:
- add the red tests first
- implement the minimum green change
- update docs/tasks if status changes
- run the ticket's verification commands
Do not touch unrelated generated artifacts.
Do not edit .claude/tasks.md as canonical task truth.
Final handoff should list files changed, commands run, and any remaining risks.
```

## Recommended Parallel Split

- Agent A: `NM-01`
- Agent B: `NM-02`
- Agent C: `NM-03`
- Agent D: `NM-04`
- Agent E: `NM-05`

Avoid assigning two agents to `tasks.md` at the same time. If `NM-02` is active, other agents should mention their task status in handoff and let the `NM-02` owner update the canonical task file, or rebase carefully before editing it.
