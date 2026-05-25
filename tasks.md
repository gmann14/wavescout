# WaveScout Tasks

Public-safe source of truth for project work. Keep sensitive spot details, credentials, private contacts, and unpublished personal context out of this file.

## Worktree Coordination

- Source of truth: this task file on the repo's `main` branch.
- In worktrees, update this file in the worktree you are using; do not edit another checkout's copy.
- Commit task updates with the code/docs change that changes task status.
- Pull or rebase from `origin/main` before long-running work and resolve task-file conflicts explicitly.

## Active

Implementation tickets live in [docs/NON-MANUAL-IMPLEMENTATION-SPECS.md](docs/NON-MANUAL-IMPLEMENTATION-SPECS.md). Start there for red/green plans, file targets, and verification commands.

- [ ] Decide long-term gallery asset hosting before public launch: keep `web/public/gallery/` in the deploy artifact, or move image delivery to object storage/CDN. Closing this needs the `NM-03` decision in `DEPLOY.md`.
- [ ] Triage the remaining local/private backlog into public-safe tracked tasks.

## Active — Manual Review Required

These need Graham or another human visual reviewer; do not assign to an implementation agent.

- [ ] Complete manual scene review for V5 swell-line research and record whether the current Sentinel-derived examples are good enough to continue.

## Done

- [x] Created public-safe task source of truth.
- [x] Promoted the public dataset through the Gate D release-readiness flow.
- [x] Drafted and iterated swell-line research spikes through the current V5 research pass.
- [x] Regenerated the local/public gallery image set and break-pin annotated variants for the web viewer.
- [x] Added local/deploy guardrails so gallery manifests cannot reference missing public image assets.
- [x] Added browser smoke coverage that fails when visible gallery images render broken.
- [x] Documented the gallery asset contract in deploy and data-contract documentation.
- [x] Fixed release-readiness helpers so the documented `python3` commands work on the repo's local Python 3.9 runtime.
- [x] Shipped the Hamburg research/docs/gallery/deploy-guard changes to `main` in merge commit `99930d1`.
- [x] Specified non-manual implementation handoff work with red/green TDD plans.
- [x] Reconciled the canonical task/backlog status after the Hamburg merge (`NM-02`).
- [x] Made release-readiness reproducible: testable `build_command_plan`, read-only `--skip-commands`, docs pinned to Python 3.12 (`NM-01`).
- [x] Added an optional CDN prefix for gallery assets with manifest-driven validation, keeping static-public hosting as the default (`NM-03`).
- [x] Split bathymetry sampling and scoring into a testable module with offshore-bearing transects and synthetic fixtures (`NM-04`).
- [x] Added a static HTML review-sheet generator for V5 swell-line scenes with escaped CSV-patch placeholders and missing-image warnings (`NM-05`).
