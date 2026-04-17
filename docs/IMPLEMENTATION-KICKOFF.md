# WaveScout Implementation Kickoff

*Updated: 2026-04-17*  
*Status: Start-here guide for the first coding cycle*

## Start Here

If implementation starts now, begin with:

1. [ROADMAP.md](ROADMAP.md)
2. [IMPLEMENTATION-BACKLOG.md](IMPLEMENTATION-BACKLOG.md)
3. [MIGRATION-STRATEGY.md](MIGRATION-STRATEGY.md)

Then execute:

1. `WS-01`
2. `WS-02`
3. `WS-03`

Do not start UI polish, ranking changes, or new feature work before those three are in flight.

## First Branches

Suggested branch sequence:

- `codex/ws-01-pipeline-test-foundation`
- `codex/ws-02-frontend-test-foundation`
- `codex/ws-03-contract-validation`

## First PR Goals

### PR 1

Goal:

- make tests runnable, even if many still fail

Must include:

- test runner setup
- fixture directories
- first failing schema tests

### PR 2

Goal:

- make frontend tests and smoke tests runnable

Must include:

- frontend test runner
- first component tests
- first e2e smoke path

### PR 3

Goal:

- introduce dataset-manifest and contract validation before payload churn

Must include:

- dataset-manifest generation or validation stub
- contract checks wired to docs

## Working Agreement

- treat docs as locked baseline unless a contradiction is found
- prefer small PRs with one dominant concern
- keep migration changes explicit and temporary
- update docs in the same PR when behavior changes

## Ready-To-Code Checklist

Before opening the first implementation PR, confirm:

- target ticket exists in [IMPLEMENTATION-BACKLOG.md](IMPLEMENTATION-BACKLOG.md)
- acceptance criteria are copied into the PR description
- relevant docs are linked in the PR description
- the PR is not mixing unrelated roadmap phases
