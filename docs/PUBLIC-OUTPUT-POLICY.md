# WaveScout Public Output Policy

*Updated: 2026-04-17*  
*Status: Normative disclosure and publication policy for public-facing outputs*

## Purpose

WaveScout handles location-sensitive information. This document defines what may be published, how precise it may be, and what must remain internal.

## Core Rule

Verification status is not publication permission.

A location can be:

- confirmed but not public
- candidate and coarse-public
- rejected and internal-only

## Publication Status Values

### `public_named`

Use only when:

- the location is already broadly public, or
- the user explicitly intends to publish it, and
- there is no known disclosure concern

Allowed:

- public name
- public point geometry
- detail page

### `public_coarse`

Use when:

- the output is useful publicly, but precise disclosure would be excessive

Allowed:

- section-level or rounded geometry
- generic candidate label
- explanation and evidence at coarse precision

Not allowed:

- exact spot naming
- exact point geometry

### `internal_only`

Use when:

- the location comes from local/private knowledge
- the publication risk is unclear
- a takedown request exists
- the result is calibration-only

Not allowed in public dataset:

- named card
- point geometry
- compare inclusion
- atlas emphasis

## Entity Rules

### Public Confirmed Spots

Requirements:

- `verification_status = confirmed`
- `publication_status = public_named`

### Local-Knowledge References

Default:

- `verification_status = confirmed`
- `publication_status = internal_only`

These may be used for calibration without public display.

### Public Candidates

Requirements:

- `verification_status = candidate`
- `publication_status = public_coarse`

Display rules:

- unnamed or generically labeled
- rounded centroid or section geometry only
- caution language mandatory

### Rejected Results

Default:

- `verification_status = rejected`
- `publication_status = internal_only`

## Coordinate Precision

Precision limits:

- `public_named`: source-appropriate public precision allowed
- `public_coarse`: round point coordinates to `3` decimal places maximum, or show only atlas-section geometry
- `internal_only`: no public coordinates

## Public Copy Rules

Public candidate copy must:

- say `candidate`
- describe evidence, not quality
- mention uncertainty

Public candidate copy must not:

- imply surfability is confirmed
- imply current conditions
- imply private/local endorsement

## Takedown And Review

The public product must support a simple report or takedown path before release.

Minimum requirement:

- a visible contact path on the site or linked policy page

If a takedown or sensitivity concern is raised:

- move the entity to `internal_only`
- remove it from promoted public datasets on the next release

## Release Gate

A release fails policy review if any are true:

- a local/private reference is exposed as `public_named`
- a candidate is shown at exact point precision without explicit policy exception
- a rejected or internal-only entity is present in public payloads
