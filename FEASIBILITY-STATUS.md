# WaveScout Feasibility Status

*Updated: 2026-04-17*  
*Status: Feasibility passed; product hardening still required*

## Decision

WaveScout should continue as an imagery-assisted discovery product.

The feasibility question was:

`Can Sentinel-2 imagery contribute useful surf evidence at known Nova Scotia spots?`

Current answer:

- yes, for some exposed and visually legible spots
- no, not as a standalone truth source
- only with strong caveats around contamination, coarse resolution, and sparse observations

## What Was Proven

Manual review established that:

- NIR imagery can make breaking-wave evidence easier to see than true-color RGB
- moderate swell scenes can produce visually useful signal
- flat or weak days can often be distinguished from active days
- the method is reproducible enough to justify pipeline work beyond ad hoc manual review

## What Was Not Proven

Feasibility did not prove that:

- every known break is recoverable
- the current automated detector is production-ready
- coarse marine context can support exact tide or “working now” claims
- the current ranking is robust against contamination and false positives

## Remaining Risks

The most important unresolved issues after feasibility are:

- cloud, snow, haze, shadow, swath-edge, and low-tide sand contamination
- cliff and headland false positives
- inconsistent score semantics across pipeline, docs, and UI
- lack of automated regression tests

## Implication for Product Direction

The correct next step is not “ship because feasibility passed.” The correct next step is:

1. harden the evidence layer
2. standardize explanation and ranking semantics
3. make the viewer honest about confidence and caveats
4. add automated coverage before release

Those steps are specified in [docs/ROADMAP.md](docs/ROADMAP.md).
