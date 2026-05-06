# WaveScout Tasks

Public-safe source of truth for project work. Keep sensitive spot details, credentials, private contacts, and unpublished personal context out of this file.

## Worktree Coordination

- Source of truth: this task file on the repo's `main` branch.
- In worktrees, update this file in the worktree you are using; do not edit another checkout's copy.
- Commit task updates with the code/docs change that changes task status.
- Pull or rebase from `origin/main` before long-running work and resolve task-file conflicts explicitly.

## Active

- [ ] Ship the Hamburg worktree to `main`: commit the research/docs/gallery/deploy-guard changes, push a replacement branch, open a PR, and merge after green checks.
- [ ] Decide long-term gallery asset hosting before public launch: keep `web/public/gallery/` in the deploy artifact for now, or move image delivery to object storage/CDN and update manifests accordingly.
- [ ] Complete manual scene review for the swell-line research outputs and record whether the current Sentinel-derived examples are good enough to continue.
- [ ] Triage the remaining local/private backlog into public-safe tracked tasks.

## Done

- [x] Created public-safe task source of truth.
- [x] Promoted the public dataset through the Gate D release-readiness flow.
- [x] Drafted and iterated swell-line research spikes through the current V5 research pass.
- [x] Regenerated the local/public gallery image set and break-pin annotated variants for the web viewer.
- [x] Added local/deploy guardrails so gallery manifests cannot reference missing public image assets.
- [x] Added browser smoke coverage that fails when visible gallery images render broken.
- [x] Documented the gallery asset contract in deploy and data-contract documentation.
- [x] Fixed release-readiness helpers so the documented `python3` commands work on the repo's local Python 3.9 runtime.
