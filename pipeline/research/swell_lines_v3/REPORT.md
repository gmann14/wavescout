# Swell-Line Detection V3 Report

*Status: spike complete; fail path reached. Owner: Graham Mann. Updated: 2026-04-23.*

## Scope

- Separate research track only. No production ranking changes.
- Same frozen 8-scene `B04` benchmark as v1 and v2.
- Change under test: keep the v2 localized Radon + FFT detector, but restrict analysis to a segment-aligned offshore corridor anchored at the spot point.
- Added diagnostics against the matched coastline-segment orientation without changing the official pass bar.

## What Changed From V2

1. Spot context is resolved from repo geometry:
   - calibration-based matched segment when available
   - otherwise best scored nearby segment, not merely the nearest raw coastline segment
2. Only pixels inside an offshore corridor are allowed to vote:
   - near edge: `250 m`
   - far edge: `1750 m`
   - alongshore half-width: `900 m`
3. Results record both:
   - azimuth delta vs Open-Meteo swell direction
   - azimuth delta vs matched segment orientation

This was meant to answer whether the v2 false positives and direction misses were mainly a bad ROI problem.

## Validation

- `venv/bin/pytest tests/pipeline/test_swell_line_detection_v3.py` -> `5 passed`
- `venv/bin/python -m py_compile pipeline/research/swell_lines_v3/__init__.py pipeline/research/swell_lines_v3/detect.py pipeline/research/swell_lines_v3/run_experiment.py`

## Official Run

Command:

```bash
venv/bin/python pipeline/research/swell_lines_v3/run_experiment.py --band B04
```

Artifacts:

- results: `pipeline/research/swell_lines_v3/results.json`
- report: `pipeline/research/swell_lines_v3/REPORT.md`

Official score:

- status: `fail`
- scenes correct: `3/8`

## Diagnostic Alternate Score

If the organized-scene direction check is evaluated against the matched segment orientation instead of Open-Meteo, the score becomes:

- diagnostic score: `4/8`

That is informative, but it is still below the `>=6/8` continuation bar, so it does **not** rescue this branch.

## Per-Spot Breakdown

| Spot | Organized scene | Flat scene | Net |
|---|---|---|---:|
| Cow Bay | `organized`, share `0.83`, wavelength `228 m`, delta vs Open-Meteo `34.00°`, delta vs segment `70.20°` -> fail on direction either way | `flat` -> pass | `1/2` |
| Lawrencetown Beach | `flat`, share `0.43`, delta vs Open-Meteo `61.33°`, delta vs segment `26.63°` -> still fails mainly on cluster share | `flat` -> pass | `1/2` |
| Hirtle's Beach | `organized`, share `0.56`, wavelength `114 m`, delta vs Open-Meteo `33.19°`, delta vs segment `11.71°` -> official fail, diagnostic near-save | `flat` -> pass | `1/2` |
| Martinique Beach | `flat`, share `0.36`, wavelength `162.86 m`, delta vs Open-Meteo `13.41°`, delta vs segment `9.61°` -> fails on cluster share; flat control still false-positive `organized` with share `1.00` | `organized` false positive -> fail | `0/2` |

## What V3 Tells Us

1. The ROI problem is real, but it is not the whole problem.
   - Hirtle's improved materially once the segment match and corridor were sensible.
   - Martinique flat still produced a decisive false positive inside the corridor.
2. Direction mismatch is sometimes real, but not dominant enough to save the method.
   - The segment-orientation diagnostic only improves the score from `3/8` to `4/8`.
3. The biggest remaining blocker is still scene-level coherence / share.
   - Lawrencetown and Martinique organized both have plausible wavelengths and, in Martinique's case, plausible direction, but the dominant cluster is not strong enough.
4. The current detector family still cannot separate Martinique flat from organized structure.

## Conclusion

This branch answers the next question honestly:

> Segment-aligned offshore ROI cleanup plus local coastline-direction diagnostics did **not** make the localized optical detector good enough to continue implementation in this form.

Operational consequence:

- no production integration work
- no more threshold grinding on the corridor-masked Radon + FFT family

If research continues, the next honest change is a different detector family, not another round of ROI tuning.
