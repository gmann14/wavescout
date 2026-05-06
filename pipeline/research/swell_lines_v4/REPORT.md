# Swell-Line Detection V4 Report

*Status: spike complete; fail path reached. Owner: Graham Mann. Updated: 2026-04-24.*

## Scope

- Separate research track only. No production ranking changes.
- Same frozen 8-scene `B04` benchmark as v1, v2, and v3.
- New detector family under test: multi-scale Morlet wavelet transects inside the segment-aligned offshore corridor.

## What Changed From V3

1. Kept the v3 spot context and segment-aligned offshore corridor.
2. Replaced the tile Radon + FFT detector with 1D wavelet analysis along multiple parallel offshore transects.
3. Searched a small azimuth band around the matched segment orientation and chose the best coherent wavelet candidate.

This branch was designed to test the exact hypothesis suggested by the wavelet literature: nonstationary nearshore wave fields may be better handled by local time/space-frequency analysis than by fixed-window FFT methods.

## Validation

- `venv/bin/pytest tests/pipeline/test_swell_line_detection_v4.py` -> `4 passed`
- `venv/bin/python -m py_compile pipeline/research/swell_lines_v4/__init__.py pipeline/research/swell_lines_v4/detect.py pipeline/research/swell_lines_v4/run_experiment.py`

## Official Run

Command:

```bash
venv/bin/python pipeline/research/swell_lines_v4/run_experiment.py --band B04
```

Artifacts:

- results: `pipeline/research/swell_lines_v4/results.json`
- report: `pipeline/research/swell_lines_v4/REPORT.md`

Official score:

- status: `fail`
- scenes correct: `4/8`

## What Improved

1. This is the first branch to improve the **official** score since the original detector family was introduced.
2. The improvement is entirely from precision:
   - all 4 flat scenes passed
   - the Martinique flat false positive disappeared
3. The detector now behaves conservatively instead of hallucinating organized structure across the corridor.

## What Still Failed

All 4 organized scenes still failed the continuation bar.

| Spot | Organized scene outcome | Flat scene outcome | Net |
|---|---|---|---:|
| Cow Bay | `flat`; only `2/11` transects retained, but chosen azimuth was otherwise plausible (`24.2°` off Open-Meteo) | `flat` pass | `1/2` |
| Lawrencetown Beach | `flat`; only `1/15` transects retained, with plausible direction (`10.7°` off Open-Meteo) | `flat` pass | `1/2` |
| Hirtle's Beach | `flat`; only `1/15` transects retained, and direction was just outside the gate (`26.9°`) | `flat` pass | `1/2` |
| Martinique Beach | `flat`; no retained transects despite plausible direction (`3.8°`) | `flat` pass | `1/2` |

## What V4 Tells Us

1. The wavelet branch improved **precision** but not **recall**.
   - It stopped calling obvious flats organized.
   - It still could not recover enough consistent organized evidence to pass the 4 organized scenes.
2. The main remaining blocker is not just direction.
   - Cow Bay and Lawrencetown both found plausible azimuths.
   - The detector still retained too few coherent transects.
3. The wavelet branch changed the failure mode in a useful way:
   - v2/v3 were too willing to believe coherent coastal texture
   - v4 is too conservative and drops most organized scenes

## Conclusion

This branch answers the v4 question honestly:

> A multi-scale wavelet transect detector is better behaved than the Radon + FFT family on flat controls, but it still does **not** recover enough organized scenes to clear the frozen `>=6/8` continuation bar.

Operational consequence:

- no production integration work
- no claim that the optical line is ready

This is the strongest optical result so far on the official bar, but it is still a fail.

Next step, if research continues:

- `docs/RESEARCH-SWELL-LINE-DETECTION-V5.md`
