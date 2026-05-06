# Swell-Line Detection V2 Report

*Status: spike complete; fail path reached. Owner: Graham Mann. Updated: 2026-04-23.*

## Scope

- Separate research track only. No changes to `pipeline/scripts/20_rank_segments.py`.
- Same frozen 8-scene benchmark as v1 from `pipeline/research/swell_lines/calibration_pairs.json`.
- Official band: `B04`.
- Method under test: localized Radon + FFT tile voting.

## Implementation Record

Files added for this spike:

- `pipeline/research/swell_lines_v2/__init__.py`
- `pipeline/research/swell_lines_v2/detect.py`
- `pipeline/research/swell_lines_v2/run_experiment.py`
- `pipeline/research/swell_lines_v2/results.json`
- `tests/pipeline/test_swell_line_detection_v2.py`
- `pipeline/research/swell_lines_v2/plots/*.png`

Local validation:

- `venv/bin/pytest tests/pipeline/test_swell_line_detection_v2.py` -> `5 passed`
- `venv/bin/python -m py_compile pipeline/research/swell_lines_v2/__init__.py pipeline/research/swell_lines_v2/detect.py pipeline/research/swell_lines_v2/run_experiment.py`

## Frozen Detector Configuration

- Preset chosen on the Cow Bay organized pilot: `s2shores`
- Frozen geometry:
  - window: `800 m × 800 m`
  - stride: `100 m`
- Local thresholds:
  - `min_local_coherence = 4.0`
  - `min_local_peak_fraction = 0.1`
- Scene thresholds:
  - `min_cluster_share = 0.5`
  - `min_cluster_tile_count = 3`
  - `min_cluster_median_coherence = 4.0`
  - `angle_bin_deg = 15`
  - `theta_step_deg = 2`

Cow Bay pilot used to freeze geometry:

| Preset | Organized classification | Organized share | Organized azimuth delta | Flat classification | Flat share |
|---|---:|---:|---:|---:|---:|
| `bergsma` | `flat` | `0.25` | `62.66°` | `flat` | `0.20` |
| `s2shores` | `organized` | `0.58` | `34.89°` | `flat` | `0.22` |

Decision: freeze `s2shores`. The smaller Bergsma-style windows did not produce a usable dominant cluster on the pilot.

## Official Run

Command:

```bash
venv/bin/python pipeline/research/swell_lines_v2/run_experiment.py --band B04 --preset s2shores --write-plots
```

Artifacts:

- results: `pipeline/research/swell_lines_v2/results.json`
- plots: `pipeline/research/swell_lines_v2/plots/*.png`

Official score:

- status: `fail`
- scenes correct: `3/8`

## Per-Spot Breakdown

| Spot | Organized result | Flat result | Net |
|---|---|---|---:|
| Cow Bay | `organized`, share `0.58`, wavelength `228 m`, azimuth delta `34.89°` -> **fail** on direction tolerance | `flat` -> **pass** | `1/2` |
| Lawrencetown Beach | `flat`, share `0.45`, wavelength `103.64 m`, azimuth delta `18.0°` -> **near miss**, fails on cluster share | `flat` -> **pass** | `1/2` |
| Hirtle's Beach | `flat`, share `0.46`, wavelength `114 m`, azimuth delta `30.94°` -> **near miss**, fails on share and direction | `flat` -> **pass** | `1/2` |
| Martinique Beach | `flat`, share `0.18`, wavelength `228 m`, azimuth delta `89.08°` -> **clear miss** | `organized`, share `0.61`, wavelength `126.67 m` -> **false positive** | `0/2` |

## What Actually Improved

- The localized detector no longer treated Cow Bay organized as obviously flat. It found a dominant cluster and classified it `organized`.
- Lawrencetown organized became a real borderline case rather than a total miss.
- The localized method produced more interpretable scene structure than v1 because the failures can now be described in terms of cluster dominance and coastal texture, not just one global spectral threshold.

## Why It Still Failed

1. The dominant cluster often existed but did not align tightly enough with the Open-Meteo direction gate.
2. The share threshold remained the bottleneck on Lawrencetown and Hirtle's even when wavelength and, in one case, azimuth looked plausible.
3. Martinique flat produced a strong, coherent false-positive cluster across a large coastal area. The diagnostic plot strongly suggests stable coastal texture / shoreline-adjacent structure can still masquerade as organized swell evidence under this method.
4. The net outcome did not improve the external decision bar at all: v1 was `3/8`; v2 is still `3/8`.

## Conclusion

This spike answers the v2 question honestly:

> Localized Radon + FFT / tile voting on Sentinel-2 `B04` did **not** clear the frozen `>=6/8` continuation bar.

Operational consequence:

- no production integration work
- no follow-on optical implementation ticket for this detector family

If research continues, it should reopen as a **new** branch, not more threshold grinding on this exact v2 detector.
