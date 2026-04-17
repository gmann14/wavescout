# Algorithm Experiments

*Updated: 2026-04-17*  
*Status: Research backlog, not the shipping roadmap*

## Purpose

This document is for research ideas that may improve detection quality later. Nothing here should outrank the delivery work in [ROADMAP.md](ROADMAP.md) unless it directly fixes a current MVP blocker.

## Candidate Research Tracks

### Swell-Line Detection

Hypothesis:

- organized offshore wave bands may help separate true break behavior from random cliff foam

Potential signals:

- periodic banding
- directionally coherent line structure
- refraction patterns around headlands

### Foam Pattern Classification

Hypothesis:

- concentrated foam zones are more promising than uniform cliff-line foam

Potential signals:

- clustered vs diffuse foam
- arc or point-like spatial signatures
- inside calm-zone presence

### Break-Type Inference

Hypothesis:

- some false positives become easier to filter if the system can distinguish beach, point, reef, slab, and cliff-like patterns

### Tidal And Shoreline-State Effects

Hypothesis:

- some apparent foam may actually be exposed wet sand or tide-dependent shoreline changes

### Multi-Resolution Or Multi-Band Screening

Hypothesis:

- combining NIR with other bands may improve separation of water foam from bright non-water surfaces

## Research Rules

- each experiment must define the failure mode it targets
- each experiment must define the evaluation set before implementation
- each experiment must state what product decision it could change
- no experiment should ship by implication; it needs its own acceptance criteria
