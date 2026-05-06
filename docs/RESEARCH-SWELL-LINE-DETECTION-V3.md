# Research: Swell-Line Detection V3 — Segment-Aligned Offshore Corridor

*Status: spike complete; fail path reached. Owner: Graham Mann. Updated: 2026-04-23.*

## Why This Existed

V2 showed two concrete weaknesses:

- coastal texture was still able to create coherent false positives
- some organized scenes looked directionally plausible, suggesting the ROI and local geometry might still be wrong

So v3 tested a narrower question:

> If the localized detector is constrained to a segment-aligned offshore corridor anchored at the spot point, does the frozen `B04` benchmark improve enough to justify continuing this optical line?

## What Was Tested

- same frozen 8 scenes
- same `B04` chips
- same localized Radon + FFT / tile voting core
- new offshore corridor mask:
  - `250–1750 m` seaward from the spot anchor
  - `±900 m` alongshore
- matched segment orientation recorded as a diagnostic, but **not** used to change the official pass bar

## Actual Outcome (2026-04-23)

Official run:

```bash
venv/bin/python pipeline/research/swell_lines_v3/run_experiment.py --band B04
```

Result:

- official score: `3/8`
- outcome: `fail`
- artifact: `pipeline/research/swell_lines_v3/results.json`
- report: `pipeline/research/swell_lines_v3/REPORT.md`

Useful additional finding:

- if organized-scene direction is checked against matched segment orientation instead of Open-Meteo, the score rises only to `4/8`

That means v3 clarified failure modes, but did not improve the go / no-go decision.

## Operational Conclusion

- no production integration work
- no more tuning on the corridor-masked Radon + FFT family

The next honest optical branch would need a **different detector family**, not just another ROI or threshold iteration.
