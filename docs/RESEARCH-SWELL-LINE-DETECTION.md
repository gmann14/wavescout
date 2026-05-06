# Research: Swell-Line Detection as a Second Evidence Signal

*Status: spike complete; fail path reached. Owner: Graham Mann. Updated: 2026-04-23.*

## 1. Motivation

The NIR foam signal (`13_detect_foam_nir.py`) tells us where bright water appears along the coast but cannot distinguish breaking waves from wet rock, cliff splash, harbour wash, or exposed wet sand (failure modes in `docs/METHODOLOGY.md` l.76–87). `docs/ROADMAP.md` l.305 defers swell-line detection as research. Foam says something bright is happening at the shoreline; organized offshore swell lineations would say *open-ocean swell is actually arriving*. Together they raise `evidence_confidence_level` and directly attack the top failure mode — foam on sheltered segments with no real swell exposure.

## 2. Background — current signal path

Today a segment’s composite score in `20_rank_segments.py` is geometry (0.35) + NIR foam (0.40) + swell-response profile (0.25). Foam is computed in GEE from a 0–200 m seaward buffer on `COPERNICUS/S2_SR_HARMONIZED` B8 with reflectance threshold 800 and SCL water masking, paired with Open-Meteo swell height/period/direction at overpass. `_coastal_context.py` penalises sheltered geometry. This spike does **not** touch that path. At most it produces a per-scene offshore organization result over a separate analysis window (~200 m–3 km seaward of the same segment) that a future ticket can decide whether to integrate.

## 3. Prior art

- **Bergsma et al., 2019** — Radon-augmented S2. Localised Radon + per-direction DFT on 10 m bands recovers dominant wavelength and azimuth. [MDPI RS 11(16):1918](https://www.mdpi.com/2072-4292/11/16/1918).
- **Zhang et al., 2025** — Angular Spectrum Method on S2 MSI. FFT on B04/B08 with inter-band time-lag (0.74 s) removing 180° ambiguity; buoy-validated RMSE 22.7° direction, 30.1 m wavelength (N=144). [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0034425725004481).
- **Almar et al., 2025** — S2Shores open-source toolbox packaging Radon+FFT for global coastal bathymetry. [Scientific Data](https://www.nature.com/articles/s41597-025-06402-w).
- **Poupardin et al., 2020** — Multi-date S2 joint celerity+wavelength; shows coherent structure survives across scenes. [MDPI RS 13(11):2149](https://www.mdpi.com/2072-4292/13/11/2149).

## 4. Physical constraints — what can a 10 m/pixel S2 scene resolve?

Nyquist sets the theoretical floor at 20 m wavelength. That is **not** the working floor. In practice, published Sentinel-2 wave-retrieval results are materially more reliable once wavelengths are roughly **70–80 m or longer**, because the signal is weak radiometric modulation of the sea surface and short-period chop is easily lost in brightness noise. For this spike, treat **~70 m as the conservative practical floor** ([Bergsma 2019](https://www.mdpi.com/2072-4292/11/16/1918); [Zhang 2025](https://www.sciencedirect.com/science/article/abs/pii/S0034425725004481)).

Deep-water linear dispersion L = gT²/(2π):

| Period T (s) | Wavelength L (m) | S2 resolvable? |
|---|---|---|
| 6 | 56 | no |
| 8 | 100 | yes |
| 10 | 156 | strong |
| 12 | 225 | strong |
| 14 | 306 | strong |

Nova Scotia open-coast groundswell runs 9–11 s in the gallery manifest for our candidate red-test days → 125–190 m deep-water wavelengths, comfortably above the practical floor. Shoaling shortens these, which is exactly why the measurement window must stay offshore rather than drift into the surf zone.

Caveats:
- **Signal source is glint-enhanced sea-surface brightness modulation, not foam.** Detectability depends on sun/view geometry and wind roughness; low cloud % is necessary but not sufficient.
- **Inter-band parallax is only needed if we later need true propagation direction over 0–360°.** For this spike’s binary "organized vs not" gate, plus an azimuth check scored mod 180, it is **not required** and should stay out of the minimum path.
- **Atmospheric haze and low local contrast** flatten modulation; existing SCL / `quality_score` help but do not guarantee a usable wave signal.
- **Whitecaps saturate** near shore — the analysis window must be *offshore* of the surf zone.

## 5. Proposed minimum experiment

Pick spots where the gallery manifest (`pipeline/data/gallery/manifest.json`) has both a clean organized-swell scene and a clean flat scene at the same location. **Freeze the 8 scenes below before implementation starts. Do not swap, add, or remove scenes after seeing detector results.** This is a triage set, not a validation set (the scenes are few and not fully independent), but it is enough for a go / no-go spike decision.

| Spot | Organized scene | Flat control |
|---|---|---|
| Cow Bay (Osbourne) | 2026-03-18 — 2.1 m @ 9.0 s, 175° | 2022-11-09 — 0.26 m @ 10.95 s |
| Lawrencetown Beach | 2023-11-19 — 3.5 m @ 10.65 s, 162° | 2022-11-09 — 0.26 m @ 10.95 s |
| Hirtle's Beach | 2023-09-05 — 1.7 m @ 9.2 s, 104° | 2024-08-30 — 0.26 m @ 9.55 s |
| Martinique Beach | 2023-11-19 — 2.92 m @ 10.35 s, 167° | 2021-10-10 — 0.22 m @ 9.5 s |

**Window.** Per spot, a 2–3 km offshore square from B04 (or B08 — TBD) using the existing bbox in `pipeline/configs/`. Reuse `13_detect_foam_nir.py` for auth, scene lookup, and image export patterns only; do **not** assume its 0–200 m seaward buffer can be reused directly for offshore chips. Mask shoreline and whitewater with a new offshore exclusion geometry that starts at least 200 m seaward of the coast-facing edge.

**Algorithm under test.** Reuse the public Radon+FFT approach from the [S2Shores toolbox](https://www.nature.com/articles/s41597-025-06402-w) rather than re-implementing. Per window, recover (peak wavelength L, peak azimuth θ, peak spectral power P).

**Success metric.**
1. On each organized scene: L in 80–250 m AND θ within ±25° of Open-Meteo `swell_direction_deg` (mod 180°).
2. On each flat scene: P below a **pre-declared** noise floor derived from the same chip geometry (for example `noise_floor_quantile` over N random rotations). Pick the single quantile once on the Cow Bay pilot, then freeze it before the 8-scene run.
3. Across 4 spots × 2 scenes = 8 total: ≥6/8 correctly classified counts as **signal-bearing enough to justify follow-up**, not "validated." Below 6/8 → no-go.

## 6. Red-test sketch

File: `tests/pipeline/test_swell_line_detection.py`

```python
# Red test: expected to fail until the detector exists.
def test_swell_line_detector_separates_organized_from_flat():
    pairs = load_calibration_pairs()  # 4 spots × (organized, flat)
    scenes_correct = 0
    for spot, organized_scene, flat_scene in pairs:
        org_chip = chip_path_for(spot, organized_scene)
        flat_chip = chip_path_for(spot, flat_scene)
        org_result = detect_swell_lines(org_chip)
        flat_result = detect_swell_lines(flat_chip)
        if (
            org_result.classification == "organized"
            and 80 <= org_result.wavelength_m <= 250
            and angular_diff_mod180(
                org_result.azimuth_deg, organized_scene["swell_direction_deg"]
            ) <= 25
        ):
            scenes_correct += 1
        if flat_result.classification == "flat":
            scenes_correct += 1
    assert scenes_correct >= 6, f"{scenes_correct}/8 scenes classified correctly; need >=6"
```

Shape intentionally mirrors `20_rank_segments.py`’s calibration-pair style. `detect_swell_lines` is a stub until implementation; the test fails red today because the stub does not exist. The test calls the detector directly. `results.json` is a reporting artifact, not the oracle for the green test.

## 7. Risks & unknowns (brutally honest)

1. **Sun-glint dependency.** 15 UTC NS overpass in winter has low sun (helps glint but shortens the usable window). Seasonal detectability variance is unknown — needs measurement.
2. **Scope creep into bathymetry.** Every prior-art paper couples detection to bathymetric inversion. We need binary "organized yes/no" plus azimuth, not depth. Risk: over-engineering a PhD inverter when a one-page FFT + peak-SNR check would do.
3. **Wind-sea false positives.** 4–7 s chop produces 25–75 m wavelengths that may or may not read as organized. Open-Meteo reports both `wave_height` and `swell_wave_height`; cross-referencing disputed scenes is the check — unknown which way it cuts.
4. **Sparse dual-scene coverage.** The gallery has ~1 truly organized (≥1.5 m / ≥9 s) scene per spot at publish-grade quality. Real validation needs ≥10 per spot; either widen the quality window or accept weaker statistics.
5. **Crossing seas / refracted multi-train fields.** A real swell scene can contain two comparable line systems; Radon / FFT may smear the peak or lock onto the wrong azimuth even when swell is present.
6. **Integration blast radius.** Adding a `swell_line_component` to `20_rank_segments.py` silently re-orders the map. Requires a `ranking_regressions.json` update and a known-spot review-gate before the weight change ships.

## 8. Go / no-go recommendation

**Conditional go, behind a 2-week time-boxed spike.** Physics is favourable at 10 m for the 8–12 s groundswell band that dominates Nova Scotia, prior art is mature and open-source (S2Shores), and the calibration set already contains workable red/green pairs. The honest concern is not the signal — it is that building a *useful evidence layer* out of it requires integration, regression, and calibration work that dwarfs the detection code. Recommendation: run the 8-scene minimum experiment first, entirely outside the ranking path, against the red test above. Only if ≥6/8 passes should we scope the ranking-integration work.

## 9. Deliverables (spike exit artifacts)

The spike produces — and nothing more:

1. `pipeline/research/swell_lines/calibration_pairs.json` — 4 spots × (organized scene id, flat scene id) + bbox + Open-Meteo swell row at overpass. Single source of truth for the 8-scene experiment.
2. `pipeline/research/swell_lines/fetch_scenes.py` — exports the 8 offshore chips (B04 or B08, TBD in §10) to `pipeline/data/research/swell_lines/chips/{scene_id}.tif`.
3. `pipeline/research/swell_lines/detect.py` — thin wrapper around S2Shores (or hand-rolled Radon+FFT if integration fails; see §12). Function `detect_swell_lines(chip_path) -> SwellLineResult(wavelength_m, azimuth_deg, peak_power, classification)`.
4. `tests/pipeline/test_swell_line_detection.py` — the red/green test in §6, wired to `calibration_pairs.json` and `detect.py`.
5. `pipeline/research/swell_lines/results.json` — per-scene classification and metrics, generated by a runner for the report and manual review. The test does **not** read this file as its oracle.
6. `pipeline/research/swell_lines/REPORT.md` — one page. Pass/fail vs §5 success metric, honest failure-mode notes, 3-line go/no-go recommendation for ranking integration.
7. `pipeline/research/swell_lines/plots/*.png` — 8 chip × (Radon image, FFT spectrum, angular diff annotation). Disposable if short on time, but the report loses teeth without them.

Nothing else. No ranking integration, no `20_rank_segments.py` touches, no web surface, no API.

## 10. Work plan (10 working days)

| Day | Task | Done when |
|---|---|---|
| 1 | Resolve the 4 spots → scene IDs by reading `pipeline/data/gallery/manifest.json` and matching dates in §5. Write `calibration_pairs.json`. | File exists; red test can load it. |
| 2 | Stand up `pipeline/research/swell_lines/` with `__init__.py`, stub `detect.py`, the red test, and a tiny runner that can later write `results.json`. | `pytest tests/pipeline/test_swell_line_detection.py` fails with `NotImplementedError` from `detect_swell_lines`. |
| 3 | Implement `fetch_scenes.py` via GEE using `13_detect_foam_nir.py` as precedent for auth/scene export only. Build the new offshore exclusion geometry; do not reuse the 0–200 m foam buffer directly. Pick B04 vs B08 with one pilot chip per band: go with whichever has higher peak-to-mean spectral SNR on the Cow Bay organized scene. | 8 `.tif` chips on disk; band choice documented in REPORT.md §"Band selection". |
| 4 | Attempt S2Shores only as a viability check. If install or first-chip ingestion is not working by mid-day, stop and switch to the fallback implementation. | By end of day, one path is chosen and the dead path is abandoned. |
| 5 | Implement the chosen detector wrapper end-to-end. | `detect_swell_lines(chip_path)` returns a populated `SwellLineResult` on at least 1 organized chip. |
| 6 | Run detector on all 8 chips. Populate `results.json`. | `pytest tests/pipeline/test_swell_line_detection.py` runs end-to-end and reports an honest red or green result; `results.json` exists for the same run. |
| 7 | Generate `plots/*.png`. Review the misses by eye: is the detector wrong, or is the Open-Meteo reference wrong (e.g. wrap swell)? Patch obvious algorithm bugs only. | 8 PNGs saved; misclassifications have a 1-line diagnosis each. |
| 8 | If red test passes (≥6/8): write `REPORT.md` recommending ranking-integration scope. If it fails: write `REPORT.md` recommending deprioritisation and naming the minimum blocker(s) plainly, without reopening scope. | REPORT.md committed. |
| 9 | Buffer — sun-glint sensitivity check (re-run 2 misses against a different clear scene at the same spot if available) OR tuning (noise-floor threshold only; nothing else). | At most one variable tuned; all tuning logged in REPORT.md. |
| 10 | Buffer — demo, writeup, decision meeting with self. | Go / no-go decision recorded in REPORT.md §Decision. |

Slip signal: if Day 3 is not done by end of Day 4, stop and replan — the spike is already at risk.

## 11. Repo layout

```
pipeline/
  research/
    swell_lines/
      __init__.py
      calibration_pairs.json
      fetch_scenes.py
      detect.py
      run_experiment.py
      results.json          # generated by run_experiment.py
      REPORT.md             # written on Day 8
      plots/                # gitignored, regeneratable
  data/
    research/
      swell_lines/
        chips/*.tif         # gitignored, regeneratable
tests/
  pipeline/
    test_swell_line_detection.py
```

Follows the existing pattern (numbered scripts live in `pipeline/scripts/`; research lives in `pipeline/research/`; tests live under `tests/` per `pytest.ini`). `pipeline/data/research/` is new — add to `.gitignore`.

## 12. Environment & dependencies

- Python 3.12 (matches repo).
- New deps, all via `pip` into the existing `venv/`: `s2shores` (primary), `scipy>=1.11` (already transitive), `scikit-image` (for `radon` fallback), `rasterio` (for `.tif` I/O).
- GEE auth already configured (see `pipeline/scripts/10_download_coastline.py` for precedent). Project: see `MEMORY.md →` Google Earth Engine reference.
- No paid services. No new cloud compute. Runs on dev laptop.
- If S2Shores cannot be installed cleanly in one afternoon (Day 4), fall back to the 60-line Radon+FFT implementation — do not break the schedule chasing a dependency.

## 13. Out of scope

Explicitly NOT part of this spike, even if they look cheap:

- Any touch to `pipeline/scripts/20_rank_segments.py`, `19_integrate_foam.py`, or `_coastal_context.py`.
- Any new field on the public contract (`evidence_confidence_level` stays untouched).
- Any web / UI surface, including "research" toggles behind a query string.
- Scaling beyond 4 spots. One paper cannot accept 50 spots' results without the red/green pairs on each.
- Bathymetric inversion. The literature couples these; we don't need depth.
- More than one tunable threshold. If the detector requires more than `noise_floor_quantile`, it's not ready to be evidence.
- Any pair-swapping or threshold-moving after the full 8-scene run. If success depends on post hoc edits to the fixture list or threshold, it is a fail, not tuning.

## 14. Exit conditions

On Day 10 exactly one of these is committed:

- **Pass path** (≥6/8): the detector runs end-to-end on the **frozen** 8-scene set with the **frozen** threshold, and REPORT.md §Decision recommends opening a follow-up ticket `WS-XX Swell-Line Evidence Integration` with (a) ranking-weight proposal, (b) regression-pair list, (c) review gate spec. This is permission to scope integration work, not a claim that the signal is validated. Spike branch squash-merges to main as research artifacts only; no production code changes.
- **Fail path** (<6/8): the detector ran end-to-end on the frozen 8-scene set and missed the bar. REPORT.md §Decision states the gap plainly and closes the spike with no further work under this ticket. A fail is not converted into a roadmap pitch.
- **Inconclusive path** (single blocker prevented an end-to-end run): REPORT.md §Decision records what failed and names the one blocker. This path is allowed only if the detector could not be run honestly; once results exist, the outcome is pass or fail, not "mixed."

Either way, the research directory stays in-tree as the durable record. No silent abandonment.

## 15. Actual outcome (2026-04-23)

The spike was implemented and run. The result landed in the **fail path**.

Official run:

- band: `B04`
- command: `venv/bin/python pipeline/research/swell_lines/run_experiment.py --band B04`
- result: `3/8`
- artifact: `pipeline/research/swell_lines/results.json`

Cross-check:

- band: `B08`
- result: `4/8`
- this did not beat the Cow Bay pilot-band rule and did not clear the `>=6/8` bar

Observed pattern:

- flat controls passed `3/4` on the official run
- organized scenes passed `0/4`
- the organized scenes often produced plausible wavelength and mod-180 azimuth, but the detector still classified them as `flat`

Interpretation:

- this specific single-window FFT detector is not strong enough to justify integration work
- the failure does **not** cleanly prove that all optical swell-line evidence is useless
- if the topic is ever reopened, it should be reopened as a **new** research spike with a different method, not as threshold-tuning on this detector

Next-step ranking if reopened later:

1. Optical v2: localized Radon + FFT / tiled detector with tile voting.
2. Optical v3: wavelet-based nearshore detector.
3. Separate SAR-based research spike.

What this result does **not** justify:

- any touch to `20_rank_segments.py`
- any new evidence field in the production contract
- any integration ticket framed as “the signal basically worked”

Drafted follow-on optical spike:

- `docs/RESEARCH-SWELL-LINE-DETECTION-V2.md`
