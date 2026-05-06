# Research: Swell-Line Detection V2 — Localized Radon + FFT / Tile Voting

*Status: spike complete; fail path reached. Owner: Graham Mann. Updated: 2026-04-23.*

## 1. Why This Exists

The first swell-line spike is complete and failed honestly:

- official `B04` run: `3/8`
- exploratory `B08` cross-check: `4/8`
- artifact record: `pipeline/research/swell_lines/results.json`
- postmortem: `pipeline/research/swell_lines/REPORT.md`

That result closes the **current detector**, not necessarily the entire research track.

The observed failure pattern matters:

- all 4 organized scenes failed
- 3 of 4 flat controls passed
- organized scenes often still produced plausible wavelength and often plausible mod-180 azimuth
- the current detector mainly failed on **scene-level classification**

So the next honest question is narrower than “does Sentinel-2 contain any signal?”:

> Does a **localized**, literature-shaped optical detector recover enough coherent tile-level evidence on the same frozen benchmark to clear the `>=6/8` continuation bar?

## 2. Why This Is The Right Next Spike

The v1 detector used one large offshore chip and one global FFT-style decision rule. That is materially simpler than the published optical methods it was supposed to approximate.

Published guidance points the other way:

- Bergsma 2019 applies Radon filtering on **local sub-domains** and reports a `30 × 20` pixel window (`300 × 200 m` at 10 m pixels) with `50 m` spacing in the real-world setup.  
  Source: https://www.mdpi.com/2072-4292/11/16/1918
- S2Shores 2025 describes Radon + Fourier processing on **800 m computation windows** to recover wave characteristics before inversion.  
  Source: https://www.nature.com/articles/s41597-025-06402-w

That is exactly the gap between what was tried and what the literature actually does.

## 3. Hypothesis

If the offshore chip is analyzed as a set of overlapping local windows rather than one global spectrum, organized scenes will show a dominant, internally consistent tile cluster in wavelength and mod-180 azimuth, while flat scenes will not.

This spike is successful only if that improved method clears the same frozen continuation bar on the same frozen scenes.

## 4. Non-Goals

This spike still does **not** include:

- any touch to `pipeline/scripts/20_rank_segments.py`
- any production evidence-field change
- any web or API surface
- bathymetric inversion
- wavelet methods
- Sentinel-1 SAR work
- ML classification

Those remain separate branches.

## 5. Benchmark — Keep The Same Frozen 8 Scenes

Do **not** reset the benchmark. Reuse:

- `pipeline/research/swell_lines/calibration_pairs.json`

The same four spot pairs remain the gate:

| Spot | Organized scene | Flat control |
|---|---|---|
| Cow Bay (Osbourne) | 2026-03-18 — 2.1 m @ 9.0 s, 175° | 2022-11-09 — 0.26 m @ 10.95 s |
| Lawrencetown Beach | 2023-11-19 — 3.5 m @ 10.65 s, 162° | 2022-11-09 — 0.26 m @ 10.95 s |
| Hirtle's Beach | 2023-09-05 — 1.7 m @ 9.2 s, 104° | 2024-08-30 — 0.26 m @ 9.55 s |
| Martinique Beach | 2023-11-19 — 2.92 m @ 10.35 s, 167° | 2021-10-10 — 0.22 m @ 9.5 s |

Reason: the entire point of v2 is to test whether the **method** improves, not whether a different scene selection improves.

## 6. Proposed Method Under Test

### Input

- Primary band: `B04`
- Same frozen offshore chips as v1, or freshly fetched `B04` chips if regeneration is needed
- Same SCL-based water masking / shoreline exclusion discipline

`B04` stays primary because the v1 pilot on Cow Bay beat `B08` on peak SNR (`18.18` vs `11.09`) and `B08` did not reverse the fail decision.

### Localized detector

For each scene:

1. Divide the offshore chip into overlapping local windows.
2. For each window:
   - run a Radon-based orientation scan over `0–180°`
   - estimate the dominant local azimuth
   - rotate or otherwise align to that azimuth
   - estimate dominant wavelength from a local Fourier peak
   - compute a local coherence score
3. Keep only windows with:
   - wavelength in `80–250 m`
   - coherence above the frozen local threshold
4. Cluster retained windows by mod-180 azimuth.
5. Reduce to a scene-level decision using:
   - dominant cluster share
   - dominant cluster median wavelength
   - dominant cluster azimuth vs Open-Meteo swell direction (mod 180)

### Scene-level classification

- `organized`:
  - a dominant azimuth cluster exists
  - dominant cluster share clears the frozen threshold
  - dominant cluster median wavelength is `80–250 m`
  - cluster azimuth is within `±25°` of Open-Meteo `swell_direction_deg` mod 180
- `flat`:
  - no dominant azimuth cluster clears the frozen threshold

This changes the unit of evidence from “one chip has one spectrum” to “one scene has many local votes.”

## 7. Structural Choice To Freeze Early

Make **one** early structural choice, then freeze it before the 8-scene run:

- Bergsma-like windows: `300 × 200 m`, `50 m` stride
- S2Shores-like windows: `800 m` computation window

Choose between those two on the Cow Bay organized pilot scene by whichever produces the clearest dominant azimuth cluster with a plausible wavelength.

After that decision:

- do not change the window geometry after seeing the full 8-scene results

## 8. Success Metric

Keep the same external bar:

1. On each organized scene:
   - scene classification = `organized`
   - dominant cluster median wavelength in `80–250 m`
   - dominant cluster azimuth within `±25°` of Open-Meteo `swell_direction_deg` mod 180
2. On each flat scene:
   - scene classification = `flat`
3. Across 8 scenes total:
   - `>=6/8` = continue research
   - `<6/8` = close the optical line in its current form

That keeps comparability with v1.

## 9. Red / Green TDD Shape

File:

- `tests/pipeline/test_swell_line_detection_v2.py`

Red test shape:

```python
def test_swell_line_detector_v2_separates_organized_from_flat():
    pairs = load_calibration_pairs()
    scenes_correct = 0
    for pair in pairs:
        organized = detect_swell_lines_v2(chip_path_for(pair, pair["organized_scene"]))
        flat = detect_swell_lines_v2(chip_path_for(pair, pair["flat_scene"]))
        if (
            organized.classification == "organized"
            and 80 <= organized.cluster_wavelength_m <= 250
            and angular_diff_mod180(
                organized.cluster_azimuth_deg,
                pair["organized_scene"]["swell_direction_deg"],
            ) <= 25
        ):
            scenes_correct += 1
        if flat.classification == "flat":
            scenes_correct += 1
    assert scenes_correct >= 6
```

Unit tests underneath that should cover:

- tile extraction
- local azimuth recovery on synthetic stripe tiles
- local wavelength recovery on synthetic stripe tiles
- scene-level vote aggregation
- flat-scene rejection when tiles disagree

## 10. Deliverables

Create a clean v2 track instead of mutating v1 in place:

1. `pipeline/research/swell_lines_v2/__init__.py`
2. `pipeline/research/swell_lines_v2/detect.py`
3. `pipeline/research/swell_lines_v2/run_experiment.py`
4. `pipeline/research/swell_lines_v2/results.json`
5. `pipeline/research/swell_lines_v2/REPORT.md`
6. `tests/pipeline/test_swell_line_detection_v2.py`
7. `pipeline/research/swell_lines_v2/plots/*.png`

Reuse:

- `pipeline/research/swell_lines/calibration_pairs.json`
- `pipeline/data/research/swell_lines/chips/*_b04.tif`

Do **not** overwrite the v1 artifacts.

## 11. Work Plan (10 Working Days)

| Day | Task | Done when |
|---|---|---|
| 1 | Scaffold `swell_lines_v2/` and write red tests for tile extraction, synthetic local recovery, and the frozen 8-scene scene-level gate. | `pytest tests/pipeline/test_swell_line_detection_v2.py` fails for the right reasons. |
| 2 | Implement tile extraction and local synthetic tests. | Synthetic azimuth / wavelength tests pass. |
| 3 | Implement Radon-based local orientation estimation. | Organized synthetic tiles recover azimuth within tolerance. |
| 4 | Implement local wavelength estimation and local coherence scoring. | Organized synthetic tiles recover wavelength in range; flat synthetic tiles stay low coherence. |
| 5 | Implement scene-level vote aggregation. | One frozen organized scene and one frozen flat scene run end-to-end. |
| 6 | Freeze the window geometry on the Cow Bay pilot (`300 × 200 m` vs `800 m`). | Choice recorded in `REPORT.md`; no further geometry changes allowed. |
| 7 | Run the frozen 8-scene experiment. | `results.json` exists with an honest score. |
| 8 | Generate plots and inspect misses. Patch only clear implementation bugs, not the benchmark. | Misclassifications have one-line diagnoses. |
| 9 | Rerun the frozen experiment once after bug fixes. | Final `results.json` and score are stable. |
| 10 | Write `REPORT.md` and close as pass or fail. | Decision is committed with no hedge. |

## 12. Risks

1. **The scenes may still be too non-stationary.** Local windows help, but mixed refracted wave fields may still not cluster cleanly.
2. **Tile-size sensitivity may become the new tuning trap.** This is why the geometry choice must be frozen early.
3. **Glint / contrast may still dominate the outcome.** A better method does not remove the optical detectability constraint.
4. **Rocky coast texture may still fake coherent line structure.** Local votes reduce this risk but do not eliminate it.
5. **Benchmark sparsity remains real.** A pass would still justify more research, not immediate production integration.

## 13. Exit Conditions

Exactly one of these outcomes is allowed:

- **Pass**: `>=6/8` on the same frozen 8 scenes with the frozen geometry choice. Outcome: open a follow-up research ticket for broader validation, still outside production.
- **Fail**: `<6/8` on the same frozen 8 scenes. Outcome: close the optical line in its current form.
- **Inconclusive**: only if the detector could not be run end-to-end at all.

Once results exist, the outcome is pass or fail.

## 14. If V2 Fails

Do **not** keep grinding thresholds on the same optical detector family.

If v2 fails, the ranked next branches are:

1. **Wavelet-based optical spike**
   - rationale: wavelets handle nonlinear and nonstationary wave fields better than one global FFT.  
     Source: https://www.mdpi.com/2077-1312/8/10/772
2. **Sentinel-1 SAR spike**
   - rationale: avoids glint dependence and sits on a much deeper wave-retrieval literature, but is a larger branch.  
     Sources: https://www.mdpi.com/2072-4292/16/6/987, https://www.mdpi.com/2072-4292/8/9/707

## 15. What I Need From The User

Nothing to draft or start this.

The only future decision needed is whether you want this exact optical v2 spike to be the next implementation target, or whether you want to skip straight to the SAR branch instead.

## 16. Actual Outcome (2026-04-23)

This spike is now complete.

- geometry was frozen on the Cow Bay pilot to the `s2shores` preset:
  - `800 m × 800 m` windows
  - `100 m` stride
- official run:

```bash
venv/bin/python pipeline/research/swell_lines_v2/run_experiment.py --band B04 --preset s2shores --write-plots
```

- official result: `3/8`
- outcome: `fail`
- artifact record: `pipeline/research/swell_lines_v2/results.json`
- postmortem: `pipeline/research/swell_lines_v2/REPORT.md`
- plots: `pipeline/research/swell_lines_v2/plots/*.png`

What that means:

- the localized optical v2 detector did **not** clear the same frozen continuation bar as v1
- no follow-up production integration work is justified from this spike
- the localized method made some misses more interpretable, but it did not improve the go / no-go score

Observed pattern:

- Cow Bay organized became `organized`, but still failed on azimuth tolerance
- Lawrencetown organized became a near miss and failed on cluster share
- Hirtle's organized also stayed just below the cluster-share bar
- Martinique flat became a strong false positive, which is the most damaging new failure mode

So the answer to the v2 question is now concrete:

> A localized Radon + FFT / tile-voting detector on Sentinel-2 `B04` is still not strong enough on this frozen benchmark to justify continued implementation in this form.
