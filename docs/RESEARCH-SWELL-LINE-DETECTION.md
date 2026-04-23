# Research: Swell-Line Detection as a Second Evidence Signal

*Status: scoping only — do not implement yet. Owner: unassigned. Updated: 2026-04-23.*

## 1. Motivation

The NIR foam signal (`13_detect_foam_nir.py`) tells us where bright water appears along the coast but cannot distinguish breaking waves from wet rock, cliff splash, harbour wash, or exposed wet sand (failure modes in `docs/METHODOLOGY.md` l.76–87). `docs/ROADMAP.md` l.305 defers swell-line detection as research. Foam says something bright is happening at the shoreline; organized offshore swell lineations would say *open-ocean swell is actually arriving*. Together they raise `evidence_confidence_level` and directly attack the top failure mode — foam on sheltered segments with no real swell exposure.

## 2. Background — current signal path

Today a segment’s composite score in `20_rank_segments.py` is geometry (0.35) + NIR foam (0.40) + swell-response profile (0.25). Foam is computed in GEE from a 0–200 m seaward buffer on `COPERNICUS/S2_SR_HARMONIZED` B8 with reflectance threshold 800 and SCL water masking, paired with Open-Meteo swell height/period/direction at overpass. `_coastal_context.py` penalises sheltered geometry. A swell-line signal would slot in as a per-scene feature over an *offshore* window (~200 m–3 km seaward of the same segment), merged into the foam component or stored as a separate `swell_line_component`.

## 3. Prior art

- **Bergsma et al., 2019** — Radon-augmented S2. Localised Radon + per-direction DFT on 10 m bands recovers dominant wavelength and azimuth. [MDPI RS 11(16):1918](https://www.mdpi.com/2072-4292/11/16/1918).
- **Zhang et al., 2025** — Angular Spectrum Method on S2 MSI. FFT on B04/B08 with inter-band time-lag (0.74 s) removing 180° ambiguity; buoy-validated RMSE 22.7° direction, 30.1 m wavelength (N=144). [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0034425725004481).
- **Almar et al., 2025** — S2Shores open-source toolbox packaging Radon+FFT for global coastal bathymetry. [Scientific Data](https://www.nature.com/articles/s41597-025-06402-w).
- **Poupardin et al., 2020** — Multi-date S2 joint celerity+wavelength; shows coherent structure survives across scenes. [MDPI RS 13(11):2149](https://www.mdpi.com/2072-4292/13/11/2149).

## 4. Physical constraints — what can a 10 m/pixel S2 scene resolve?

Nyquist sets the resolvable floor at 20 m wavelength. In practice Radon/ASM papers cite a reliable floor near **60–80 m** because the signal comes from sea-surface brightness modulation (sun glint, orbital-velocity Bragg analogues) that degrades for short chop ([Bergsma 2019](https://www.mdpi.com/2072-4292/11/16/1918); [Zhang 2025](https://www.sciencedirect.com/science/article/abs/pii/S0034425725004481)).

Deep-water linear dispersion L = gT²/(2π):

| Period T (s) | Wavelength L (m) | S2 resolvable? |
|---|---|---|
| 6 | 56 | marginal |
| 8 | 100 | yes |
| 10 | 156 | strong |
| 12 | 225 | strong |
| 14 | 306 | strong |

Nova Scotia open-coast groundswell runs 9–11 s in the gallery manifest for our candidate red-test days → 125–190 m deep-water wavelengths, comfortably above the practical floor. Shoaling shortens these; a 150 m deep-water swell at 8 m depth is ~70 m, near the floor.

Caveats:
- **Signal source is sun glint, not foam.** Detectability depends on sun azimuth/elevation and wind roughness; overcast or low-glint scenes may fail even at low cloud % — unknown, needs measurement.
- **Inter-band parallax (0.74–1.005 s across 10 m bands) is the only way to disambiguate 180° direction** ([Zhang 2025](https://www.sciencedirect.com/science/article/abs/pii/S0034425725004481)); without it, azimuth is mod 180° — still fine for a binary "organized vs not" gate.
- **Atmospheric haze** flattens modulation; filter with existing SCL / `quality_score`.
- **Whitecaps saturate** near shore — the analysis window must be *offshore* of the surf zone.

## 5. Proposed minimum experiment

Pick spots where the gallery manifest (`pipeline/data/gallery/manifest.json`) has both a clean organized-swell scene and a clean flat scene at the same location (all scenes `quality_score ≥ 85`, `cloud_pct < 8`):

| Spot | Organized scene | Flat control |
|---|---|---|
| Cow Bay (Osbourne) | 2026-03-18 — 2.1 m @ 9.0 s, 175° | 2022-11-09 — 0.26 m @ 10.95 s |
| Lawrencetown Beach | 2023-11-19 — 3.5 m @ 10.65 s, 162° | 2022-11-09 — 0.26 m @ 10.95 s |
| Hirtle's Beach | 2023-09-05 — 1.7 m @ 9.2 s, 104° | 2024-08-30 — 0.26 m @ 9.55 s |
| Martinique Beach | 2023-11-19 — 2.92 m @ 10.35 s, 167° | 2021-10-10 — 0.22 m @ 9.5 s |

**Window.** Per spot, a 2–3 km offshore square from B04 (or B08 — TBD) using the existing bbox in `pipeline/configs/`. Mask shoreline and whitewater via a ≥200 m inward offset of the seaward buffer already built in `13_detect_foam_nir.py`.

**Algorithm under test.** Reuse the public Radon+FFT approach from the [S2Shores toolbox](https://www.nature.com/articles/s41597-025-06402-w) rather than re-implementing. Per window, recover (peak wavelength L, peak azimuth θ, peak spectral power P).

**Success metric.**
1. On each organized scene: L in 80–250 m AND θ within ±25° of Open-Meteo `swell_direction_deg` (mod 180°).
2. On each flat scene: P below the scene-specific noise floor (e.g., bottom quartile of P across N random rotations of the same window).
3. Across 4 spots × 2 scenes = 8 total: ≥6/8 correctly classified to count as signal-bearing. Below 6/8 → no-go.

## 6. Red-test sketch

File: `pipeline/tests/test_swell_line_detection.py`

```python
# Red test: expected to fail until the detector exists.
def test_swell_line_detector_separates_organized_from_flat():
    pairs = load_calibration_pairs()  # 4 spots × (organized, flat)
    correct = 0
    for spot, organized_scene, flat_scene in pairs:
        org_result = detect_swell_lines(spot, organized_scene)
        flat_result = detect_swell_lines(spot, flat_scene)
        if (
            org_result.classification == "organized"
            and 80 <= org_result.wavelength_m <= 250
            and angular_diff_mod180(
                org_result.azimuth_deg, organized_scene["swell_direction_deg"]
            ) <= 25
            and flat_result.classification == "flat"
        ):
            correct += 1
    assert correct >= 6, f"{correct}/8 pairs classified correctly; need >=6"
```

Shape intentionally mirrors `20_rank_segments.py`’s calibration-pair style. `detect_swell_lines` is a stub until implementation; the test fails red today because the stub does not exist.

## 7. Risks & unknowns (brutally honest)

1. **Sun-glint dependency.** 15 UTC NS overpass in winter has low sun (helps glint but shortens the usable window). Seasonal detectability variance is unknown — needs measurement.
2. **Scope creep into bathymetry.** Every prior-art paper couples detection to bathymetric inversion. We need binary "organized yes/no" plus azimuth, not depth. Risk: over-engineering a PhD inverter when a one-page FFT + peak-SNR check would do.
3. **Wind-sea false positives.** 4–7 s chop produces 25–75 m wavelengths that may or may not read as organized. Open-Meteo reports both `wave_height` and `swell_wave_height`; cross-referencing disputed scenes is the check — unknown which way it cuts.
4. **Sparse dual-scene coverage.** The gallery has ~1 truly organized (≥1.5 m / ≥9 s) scene per spot at publish-grade quality. Real validation needs ≥10 per spot; either widen the quality window or accept weaker statistics.
5. **Integration blast radius.** Adding a `swell_line_component` to `20_rank_segments.py` silently re-orders the map. Requires a `ranking_regressions.json` update and a known-spot review-gate before the weight change ships.

## 8. Go / no-go recommendation

**Conditional go, behind a 2-week time-boxed spike.** Physics is favourable at 10 m for the 8–12 s groundswell band that dominates Nova Scotia, prior art is mature and open-source (S2Shores), and the calibration set already contains workable red/green pairs. The honest concern is not the signal — it is that building a *useful evidence layer* out of it requires integration, regression, and calibration work that dwarfs the detection code. Recommendation: run the 8-scene minimum experiment first, entirely outside the ranking path, against the red test above. Only if ≥6/8 passes should we scope the ranking-integration work.
