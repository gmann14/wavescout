# Research: Swell-Line Detection V5 — Signal Validation And Benchmark Expansion

*Status: proposed. Owner: Graham Mann. Drafted: 2026-04-24.*

## 1. Why This Exists

V1 through V4 answered one narrow question honestly: the current Sentinel-2 optical detector families do **not** clear the frozen `>=6/8` continuation bar.

The best official result so far is V4 at `4/8`:

- all 4 flat scenes pass
- all 4 organized scenes still fail

That changes the next question.

The main uncertainty is no longer "can another detector threshold rescue the score?" The main uncertainty is:

> Are the current "organized" scenes actually visually positive for offshore swell lines in Sentinel-2, or are they only meteorologically plausible organized-swell candidates?

Until that is answered, another detector spike would blur together two different failure modes:

- the imagery / scene selection is weak
- the imagery is usable, but the detector recall is weak

## 2. What V1–V4 Do And Do Not Prove

What the current work **does** prove:

- the frozen 8-scene benchmark is a valid go / no-go triage set
- the existing optical detector families are not good enough
- flat controls are now reasonably well behaved

What the current work **does not** prove:

- that the 4 organized scenes contain clearly visible crest-line signal in the corridor
- that Sentinel-2 optical imagery is generally unusable for this problem
- that the benchmark selection is wrong

The organized labels in `pipeline/research/swell_lines/calibration_pairs.json` are based on swell metadata and image quality, not on frozen human confirmation that coherent crest lines are visibly recoverable inside the actual offshore corridor.

## 3. Research Question

Before any V5 detector exists, answer two questions:

1. Among the current 4 frozen organized scenes, how many are **visually clear positives** for swell-line structure inside the corridor?
2. Across a broader quality-filtered development set of organized-swell candidates from the same 4 spots, what fraction are visually clear positives?

This spike is about **signal validation**, not model improvement.

## 4. Scope

In scope:

- Sentinel-2 only
- `B04` only
- same 4 spots as the frozen benchmark
- manual visual review of corridor chips
- reproducible expansion of organized-swell candidate scenes
- a written go / no-go interpretation

Out of scope:

- any new detector implementation
- any production ranking integration
- Sentinel-1 SAR
- ML labeling or training
- benchmark resetting

The frozen 8 scenes stay untouched as the held-out bar.

## 5. Benchmark Design

Keep two separate sets:

### Held-out set

- the existing frozen 8 scenes in `pipeline/research/swell_lines/calibration_pairs.json`
- never changed
- used only for interpretation, not for tuning

### Development review set

Build a larger organized-candidate set from the same 4 spots:

- include the existing 4 frozen organized scenes
- pull from the larger per-spot foam manifests rather than the curated gallery manifest
- refresh scene metadata from GEE for dates after the latest local manifest date
- target a balanced broad review bank of up to `9` scenes per spot (`1` frozen + `8` additional)

Broad-profile candidate filters:

- same spot
- `cloud_pct <= 15`
- `quality_score >= 75`
- `swell_height_m >= 1.0`
- `swell_period_s >= 7.0`

If a spot has fewer than 8 additional candidates meeting those filters, keep the shortfall and record it. Do **not** backfill from a different spot.

Reason: this step is trying to separate scene quality / signal availability from detector failure while keeping geography fixed, and the stricter gallery-style pool was too sparse for a useful manual review bank.

Current repo snapshot note:

- as of 2026-04-24, the expanded scene catalog contains `445` scene-level records across the 4 spots
- the lightweight GEE refresh added `16` new post-March scene records
- the current broad review bank contains `33` organized candidates, which is close enough to the `36`-scene balanced target to proceed honestly

## 6. Review Rubric

Each organized candidate scene gets one corridor-level label after visual review:

- `clear_positive`
  - multiple roughly parallel offshore crest lines are visibly present in the corridor
  - orientation is coherent enough that a detector should plausibly recover it
- `ambiguous`
  - some line-like structure exists, but it is weak, fragmented, or too mixed to be a fair detector target
- `clear_negative`
  - no convincing organized offshore crest-line structure is visible in the corridor

Review rules:

- review the same corridor geometry used in V4
- label from the image, not from swell metadata
- record one short note per scene explaining the label
- freeze labels once assigned

This is the minimum needed to answer whether current "organized" means "visually usable."

## 7. Interpretation Matrix

This spike should end with one of these readings:

### Detector problem

- most development candidates are `clear_positive`
- at least 3 of the 4 frozen organized scenes are `clear_positive`

Interpretation:

- Sentinel-2 likely contains usable optical signal here
- current detector family is the main bottleneck

### Selection problem

- development set contains a healthy number of `clear_positive` scenes
- but the frozen organized scenes are mostly `ambiguous` or `clear_negative`

Interpretation:

- the benchmark positives were poorly chosen as optical targets
- the held-out bar should remain frozen, but future detector research should not treat those 4 scenes as proof of no signal

### Sensor / use-case problem

- most development candidates are `clear_negative`

Interpretation:

- meteorologically organized swell does not reliably produce visible optical crest lines for this corridor setup
- more optical detector work is unlikely to pay off

### Inconclusive

- the distribution is mostly `ambiguous`

Interpretation:

- the optical signal is too weak or inconsistent to support a fair go / no-go detector program

## 8. Exit Conditions

Use development-set label shares, excluding flats:

- `clear_positive >= 60%`
  - optical signal is strong enough to justify one more detector branch
- `clear_positive <= 30%`
  - close the Sentinel-2 optical line
- otherwise
  - inconclusive; do not start another detector spike until the scene-selection logic is tightened

Also report the frozen 4 organized-scene breakdown separately:

- `0–1/4 clear_positive` strongly suggests the benchmark positives were weak optical targets
- `3–4/4 clear_positive` strongly suggests detector recall is the main issue

These are interpretation aids, not a replacement for the frozen 8-scene held-out bar.

## 9. Deliverables

1. `pipeline/research/swell_lines_v5/candidate_scenes.json`
2. `pipeline/research/swell_lines_v5/scene_reviews.csv`
3. `pipeline/research/swell_lines_v5/summary.json`
4. `pipeline/research/swell_lines_v5/REPORT.md`
5. `tests/pipeline/test_swell_line_detection_v5.py`

Optional but useful:

- contact-sheet or per-scene diagnostic PNGs under `pipeline/research/swell_lines_v5/plots/`

## 10. Red / Green TDD Shape

This spike is data-first, but the plumbing should still be testable.

Red test shape:

```python
def test_signal_validation_summary_routes_to_expected_decision():
    summary = summarize_scene_reviews(
        reviewed_scenes=[
            {"label": "clear_positive"},
            {"label": "clear_positive"},
            {"label": "clear_positive"},
            {"label": "clear_positive"},
            {"label": "clear_positive"},
            {"label": "clear_positive"},
            {"label": "ambiguous"},
            {"label": "clear_negative"},
            {"label": "clear_negative"},
            {"label": "clear_negative"},
        ],
        frozen_organized_labels=[
            "clear_positive",
            "clear_positive",
            "clear_positive",
            "ambiguous",
        ],
    )
    assert summary["decision"] == "continue_optical_detector_research"
```

Unit tests underneath that should cover:

- candidate-scene selection from metadata
- stable ordering and freezing of the candidate set
- review-file schema validation
- label-share summary math
- exit-condition routing

## 11. Work Plan (7 Working Days)

| Day | Task | Done when |
|---|---|---|
| 1 | Scaffold `swell_lines_v5/` and write red tests for candidate selection, review summary, and decision routing. | `pytest tests/pipeline/test_swell_line_detection_v5.py` fails for the right reasons. |
| 2 | Implement candidate-scene selection from existing metadata and freeze the development review set. | `candidate_scenes.json` exists and is reproducible. |
| 3 | Generate chips or review artifacts for the development set using the V4 corridor geometry. | Reviewable scene assets exist for all selected candidates. |
| 4 | Label the 4 frozen organized scenes first. | The benchmark-positive question is explicitly answered. |
| 5 | Label the remaining development candidates. | `scene_reviews.csv` is complete with notes. |
| 6 | Compute label shares and route to pass / fail / inconclusive. | `summary.json` and a draft conclusion exist. |
| 7 | Write `REPORT.md` and close with a clear operational decision. | The next move is unambiguous. |

## 12. Operational Consequence

Do **not** build another detector branch until this spike answers whether the optical positives are visually real.

If this spike says the signal is there, then a future detector spike is justified.
If this spike says the signal is mostly absent or ambiguous, then Sentinel-2 optical should be closed or deprioritized in favor of a separate Sentinel-1 SAR branch.
