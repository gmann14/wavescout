# Swell-Line Spike Report

Status: complete.

## Decision

Fail. The frozen 8-scene `B04` run scored `3/8`, below the `>=6/8` continuation bar.

This spike should be treated as answered. The current Sentinel-2 swell-line detector is **not** ready to enter ranking integration work.

## Execution Record

- Environment: repo-local `venv`
- Runtime deps installed for the spike: `numpy`, `requests`, `earthengine-api`, `rasterio`, `Pillow`, `python-dotenv`, `pytest`
- Earth Engine project used for fetch: `seotakeoff`
- Frozen chips fetched to: `pipeline/data/research/swell_lines/chips/`

Commands run:

```bash
venv/bin/python pipeline/research/swell_lines/fetch_scenes.py --band B04 --project seotakeoff
venv/bin/python pipeline/research/swell_lines/run_experiment.py --band B04
venv/bin/python pipeline/research/swell_lines/fetch_scenes.py --band B08 --project seotakeoff
venv/bin/python pipeline/research/swell_lines/run_experiment.py --band B08
```

## Band Selection

- Pilot scene: `cow-bay`, organized date `2026-03-18`
- `B04`: peak SNR `18.18`
- `B08`: peak SNR `11.09`
- Official experiment band: `B04`

## Result

- Official run: `venv/bin/python pipeline/research/swell_lines/run_experiment.py --band B04`
- Output: `pipeline/research/swell_lines/results.json`
- Score: `3/8`

Per-scene pattern:

- Flat controls passed `3/4`
- Organized scenes passed `0/4`
- The organized scenes usually landed in-range on wavelength and often on mod-180 azimuth, but the detector still classified them as `flat`

Detailed outcome on the official `B04` run:

| Spot | Organized scene | Flat control | Pair score |
|---|---|---|---|
| Cow Bay | fail — `flat`, `L=178.2 m`, `Δaz=12.3°`, `peak_fraction=0.0213` | pass | `1/2` |
| Lawrencetown Beach | fail — `flat`, `L=247.6 m`, `Δaz=12.1°`, `peak_fraction=0.0360` | fail — false positive `organized` | `0/2` |
| Hirtle's Beach | fail — `flat`, `L=89.5 m`, `Δaz=23.3°`, `peak_fraction=0.0226` | pass | `1/2` |
| Martinique Beach | fail — `flat`, `L=241.8 m`, `Δaz=25.6°`, `peak_fraction=0.0088` | pass | `1/2` |

Interpretation:

- The main failure mode was **not** obviously “no wavelength signal.”
- The main failure mode was that organized scenes produced plausible wavelengths and often plausible mod-180 azimuths, but the current classifier still rejected them as `flat`.
- That points to a weak **classification rule / windowing strategy** in the current detector, not a clean proof that all optical swell-line structure is absent.

## Cross-Check

- Exploratory `B08` rerun improved only to `4/8`
- `B08` did not clear the bar and did not beat the pilot-band selection rule
- `B08` therefore does **not** change the spike decision

## Why The Current Method Failed

1. The implementation is a **single-window FFT detector** with a concentration gate. That is materially simpler than the localized Radon + Fourier methods in the cited optical literature.
2. A 2–3 km offshore chip is likely too coarse for mixed, refracted, nearshore wave fields. The current detector assumes more stationarity than the scenes appear to have.
3. The current decision rule leans heavily on `peak_fraction`, which suppressed all four organized scenes in the official run.
4. The current method is therefore not strong enough to justify production integration, even though it sometimes recovers plausible wavelength and azimuth.

## Recommended Next Steps

Immediate:

1. Treat this spike as closed in the **fail path**.
2. Do not open a production integration ticket for swell-line evidence.
3. Keep the artifacts in-tree as the durable record: frozen pairs, chips, detector, `results.json`, and this report.

If research is reopened later, do it as a **new** spike with a different method and a fresh go / no-go decision. Ranked options:

1. **Optical v2 — localized Radon + FFT / tiled detector.**
   - Replace the single global FFT over one large chip with smaller overlapping windows and tile voting.
   - This is the most direct next step because it aligns with Bergsma 2019 and S2Shores-style processing.
2. **Optical v3 — wavelet-based nearshore detector.**
   - If the main issue is non-stationary coastal structure, wavelets are a better fit than one global spectrum.
3. **Sensor switch — Sentinel-1 SAR research spike.**
   - This avoids the optical glint dependency, but it is a materially larger research branch and should be scoped separately.

Do not reopen with:

- threshold-only tuning of the current detector until it “passes”
- inter-band parallax as the first salvage move
- ML as the first salvage move without a proper labeled set

## What I Need From The User

Nothing immediate.

If you want to continue beyond this fail result, the only decision I need is which of these paths you want documented next:

1. Close this out and leave the record as-is.
2. Draft a new optical v2 spike around localized Radon + FFT / tiled voting.
3. Draft a separate SAR-based spike.

Drafted follow-on optical spike:

- `docs/RESEARCH-SWELL-LINE-DETECTION-V2.md`
