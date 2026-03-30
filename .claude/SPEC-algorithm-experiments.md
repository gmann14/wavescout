# Spec: Algorithm Experiments for Automated Spot Discovery

> Phase 5 experiments using the visual atlas and human labels as ground truth to develop multi-layer automated break detection.

## Problem

Foam fraction alone cannot reliably distinguish surfable breaks from snow, cloud edges, cliff impact, or bright sand at 10m resolution. This was confirmed during manual validation (March 26-27, 2026). However, multiple independent signals — when combined — should separate real breaks from noise.

The visual atlas (Phase 2.7) provides a browsable tool for manual spot discovery. As Graham flags potential breaks in the atlas, those labels become ground truth for training and evaluating automated detection algorithms.

## Approach

Five complementary algorithms, each attacking the problem from a different angle. Real breaks should score high on multiple methods simultaneously. False positives (snow, cloud, cliff) should only trigger one or two.

### Algorithm 1: Differential Foam Maps

**Concept**: Subtract a flat-day NIR image from a swell-day NIR image. Real breaks light up; static features (sand, rocks, snow on land) cancel out.

**Implementation**:
- For each section/segment, select pairs: one flat-day scene (swell < 0.5m, QS >= 80) and one swell-day scene (swell > 1.5m, QS >= 80)
- Compute pixel-level difference: `diff = NIR_swell - NIR_flat`
- Threshold the difference map: pixels with `diff > T` are "swell-activated"
- Count swell-activated pixels in the nearshore buffer (0-200m seaward)
- Repeat across multiple pairs, compute consistency

**Key insight**: Snow on land appears in both flat and swell images, so it cancels. Clouds are random, so they average out across pairs. Only foam that appears specifically when swell is present survives.

**Output per segment**: `differential_foam_score` (0-1), `differential_consistency` (fraction of pairs showing activation)

### Algorithm 2: Temporal Stacking

**Concept**: Stack 20+ high-swell scenes. Real breaks appear at the same pixels repeatedly. Noise is spatially random.

**Implementation**:
- Collect all scenes for a segment where swell > 1.0m and QS >= 70
- For each scene, create a binary foam mask (NIR > threshold on water pixels)
- Stack all masks and compute per-pixel frequency: `freq[x,y] = count(foam) / count(scenes)`
- Pixels with `freq > 0.3` (foam in >30% of high-swell scenes) are "persistent break zones"
- Compute total area of persistent break zones per segment

**Key insight**: A real break fires at the same location every time swell arrives. Snow and clouds hit random pixels each time.

**Output per segment**: `persistent_foam_area_m2`, `persistent_foam_pixel_count`, `max_pixel_frequency`

**GEE implementation**: Use `ee.ImageCollection.reduce(ee.Reducer.frequencyHistogram())` or `ee.Reducer.mean()` on binary masks — all server-side, no image downloads.

### Algorithm 3: Swell-Direction Response

**Concept**: Real breaks only activate on specific swell directions. A segment that shows foam equally on N, S, E, W swell is likely noise. A segment that fires specifically on SE swell (consistent with its orientation) is likely real.

**Implementation**:
- Group observations by swell direction (8 compass bins from script 14)
- For each bin, compute mean foam fraction
- Calculate direction concentration: how peaked is the distribution?
  - `concentration = max_bin_foam / mean_all_bins_foam` (higher = more directional)
- Check alignment: does the peak foam direction align with the segment's exposure direction?
  - `alignment_score = 1.0 - abs(peak_dir - exposure_dir) / 180.0`

**Key insight**: A south-facing beach should respond to S/SE swell. If it responds equally to N swell, that foam is likely not from breaking waves.

**Output per segment**: `direction_concentration`, `peak_direction`, `alignment_score`, `direction_response_map` (foam per direction bin)

### Algorithm 4: Spatial Pattern Recognition

**Concept**: Different break types produce distinct spatial foam patterns at 10m resolution.
- Point breaks: curved foam line extending from a headland
- Beach breaks: parallel bar of foam along the shoreline
- Reef breaks: localized foam cluster offshore

**Implementation**:
- On high-swell scenes, extract the foam mask (binary)
- Compute spatial metrics on foam clusters:
  - `elongation`: ratio of major to minor axis (high for point breaks)
  - `orientation_angle`: angle of the foam line relative to shore
  - `distance_from_shore`: mean distance of foam pixels to shoreline
  - `curvature`: how curved is the foam line (high for point breaks)
  - `parallelism`: how parallel is the foam line to shore (high for beach breaks)
- Classify: point (elongated + curved + off headland), beach (parallel + near shore), reef (clustered + offshore)

**Note**: This is the most experimental algorithm. At 10m resolution, foam is only 1-5 pixels wide. Pattern recognition may not be feasible until higher-resolution imagery is available. Start with simple metrics and evaluate whether they separate known break types.

**Output per segment**: `break_type_guess` (point/beach/reef/unknown), `pattern_confidence`, spatial metric values

### Algorithm 5: Multi-Layer Ensemble

**Concept**: Combine all four algorithms plus geometry score into a single automated discovery score.

```python
discovery_score = (
    w1 * differential_foam_score
  + w2 * normalize(persistent_foam_area)
  + w3 * alignment_score * direction_concentration
  + w4 * pattern_confidence
  + w5 * (geometry_score / 100)
)
```

Initial weights: equal (0.20 each). Tune using human labels as ground truth.

**Threshold**: Segments with `discovery_score > T` are flagged as "candidate breaks" for human review.

## Ground Truth: Human Labels from Atlas

The atlas labeling UI (Phase 2.7, remaining work) provides the training data:

### Label types

```typescript
interface BreakLabel {
  section_id: string;
  segment_ids: string[];       // which segments contain the break
  lat: number;
  lon: number;
  label: "confirmed_break" | "possible_break" | "not_a_break" | "cliff_foam" | "sand_artifact";
  break_type?: "point" | "beach" | "reef" | "unknown";
  notes: string;
  scenes_reviewed: string[];   // which scene dates were examined
  flagged_by: string;          // "graham"
  flagged_at: string;          // ISO timestamp
}
```

### Label collection workflow

1. Graham browses atlas sections, reviewing swell-day images
2. Flags potential breaks with coordinates and notes
3. Also flags obvious non-breaks (cliff foam, sand) as negative examples
4. Labels are stored in `pipeline/data/labels/break_labels.json`

### Minimum label requirements

- At least 30 confirmed breaks (including the 20+ known spots)
- At least 50 negative examples (cliff foam, sand, cloud artifacts)
- At least 10 "possible" labels for ambiguous cases

## Evaluation Metrics

### Per-algorithm evaluation

For each algorithm independently, compute against human labels:

- **Precision**: Of segments flagged as breaks, how many are real? (target: > 0.6)
- **Recall**: Of known breaks, how many are flagged? (target: > 0.8)
- **F1**: Harmonic mean of precision and recall (target: > 0.65)

### Ensemble evaluation

- **Precision@K**: Of the top K ranked segments, how many are real breaks?
- **Known spot recovery**: Do the 20+ known spots appear in the top 5% of ranked segments?
- **False positive rate by type**: What fraction of false positives are cliff foam vs. cloud vs. sand?

### Calibration against known spots

The 14 spots from `12_calibrate.py` (which ranked 88-94th percentile by geometry alone) should rank even higher with multi-layer scoring. If they drop, something is wrong.

## Pipeline Script Structure

### New scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `20_differential_foam.py` | Flat-vs-swell difference maps | GEE scenes, foam detections | `differential_foam_scores.json` |
| `21_temporal_stack.py` | Persistent foam zone detection | GEE scenes (20+ per segment) | `temporal_stack_scores.json` |
| `22_direction_response.py` | Swell-direction analysis | Foam detections + profiles | `direction_response_scores.json` |
| `23_spatial_patterns.py` | Foam cluster shape analysis | GEE scenes (binary masks) | `spatial_pattern_scores.json` |
| `24_ensemble_rank.py` | Combine all signals | All above + geometry + labels | `ensemble_ranked_segments.json` |

### Execution order

Scripts 20-23 are independent and can run in parallel. Script 24 depends on all four.

### GEE compute budget

- Scripts 20 and 21 require per-pixel GEE operations across many scenes per segment
- Estimate: 16,939 segments x 20+ scenes each = significant GEE compute
- Strategy: start with top 500 geometry-scored segments, expand if results are promising
- Use `ee.batch.Export` for heavy jobs, process results locally

## Expected Output

The final output is a ranked list of candidate segments:

```json
{
  "segment_id": "seg-04231",
  "discovery_score": 0.82,
  "confidence": "high",
  "evidence": {
    "differential": 0.71,
    "temporal": 0.88,
    "directional": 0.79,
    "spatial": 0.62,
    "geometry": 0.72
  },
  "break_type_guess": "beach",
  "peak_swell_direction": "SE",
  "estimated_activation": "1.2m",
  "nearest_known_spot": "lawrencetown-beach (1.4km)",
  "human_label": null
}
```

Top candidates without human labels are the most interesting — they are potential undiscovered breaks that the algorithm found but a human hasn't verified yet.

## Effort Estimate

| Task | Time |
|------|------|
| Differential foam (script 20) | 4-6h |
| Temporal stacking (script 21) | 4-6h |
| Direction response (script 22) | 2-3h (mostly reuses script 14 data) |
| Spatial patterns (script 23) | 6-8h (most experimental) |
| Ensemble ranking (script 24) | 3-4h |
| Label collection by Graham | 5-10h (ongoing, manual) |
| Evaluation + tuning | 4-6h |
| **Total** | **28-43h** |

This is the most technically ambitious phase. Expect iteration — the first pass will likely have mediocre precision, and weights/thresholds will need tuning against human labels.

## Dependencies

- Visual atlas complete (done — 2,839 sections)
- Atlas labeling UI built (not yet — needed for ground truth collection)
- Foam detections for all configured spots (done)
- Geometry scores for all segments (done)
- GEE compute quota sufficient for per-pixel operations at scale

## Open Questions

1. **Should we run algorithms on all 16,939 segments or start with a subset?** Running on the top 500 by geometry score is cheaper and covers the most likely candidates. But undiscovered breaks may be in geometrically unremarkable locations.
2. **How many human labels do we need before the ensemble is useful?** Minimum 30 positives + 50 negatives suggested, but more is better. Could bootstrap with known spots as initial positives.
3. **Is 10m resolution sufficient for spatial pattern recognition (Algorithm 4)?** Point break foam lines are 1-3 pixels wide. May need to defer this algorithm until higher-res imagery (Planet, Maxar) is explored.
4. **Temporal stacking memory**: Stacking 20+ full scenes per segment in GEE could hit memory limits. May need to work with pre-computed binary masks rather than raw NIR imagery.
5. **Seasonal confounds**: Winter scenes have the best swell but also snow. Differential maps help (snow cancels), but temporal stacking on winter-only scenes could still be biased. Consider seasonal stratification.
