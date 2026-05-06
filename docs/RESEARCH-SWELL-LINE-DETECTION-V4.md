# Research: Swell-Line Detection V4 — Multi-Scale Wavelet Transects

*Status: spike complete; fail path reached. Owner: Graham Mann. Updated: 2026-04-24.*

## Why This Existed

V3 showed that corridor cleanup helped interpretability but did not fix the detector family. The next honest optical change was a different spectral method for nonstationary nearshore wave fields.

So v4 tested:

> If the segment-aligned offshore corridor is kept, but the detector switches from tiled FFTs to multi-scale Morlet wavelet transects, does the frozen `B04` benchmark improve enough to justify continuing this optical line?

## What Was Tested

- same frozen 8 scenes
- same `B04` chips
- same segment-aligned offshore corridor idea from v3
- new detector family:
  - multiple parallel transects through the corridor
  - Morlet CWT wavelength recovery on each transect
  - small azimuth search around the local segment orientation
  - scene classification from retained-transect share and wavelength-cluster coherence

## Actual Outcome (2026-04-24)

Official run:

```bash
venv/bin/python pipeline/research/swell_lines_v4/run_experiment.py --band B04
```

Result:

- official score: `4/8`
- outcome: `fail`
- artifact: `pipeline/research/swell_lines_v4/results.json`
- report: `pipeline/research/swell_lines_v4/REPORT.md`

Interpretation:

- this is the best official optical score so far
- the gain came from eliminating the Martinique flat false positive
- all 4 flat scenes passed
- all 4 organized scenes still failed

So v4 improved precision, but not recall.

## Operational Conclusion

- no production integration work
- no more claims that the current optical track is close to ready

If research continues after this, it should be because `4/8` is meaningfully better than `3/8`, not because the current branch secretly passed.

The next honest step is documented in:

- `docs/RESEARCH-SWELL-LINE-DETECTION-V5.md`
