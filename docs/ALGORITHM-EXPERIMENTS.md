# Algorithm Experiments & Future Detection Ideas

*Design exploration — not implemented yet. Ideas for improving break detection quality and making the scoring system modular.*

## Current Limitations

The current pipeline detects foam in a nearshore buffer and correlates with swell. This works for obvious breaks but has false positives (cliffs, rocky shores) and misses nuance (break quality, wave shape, type).

## Experiment Ideas

### 1. Swell Line Detection (HIGH PRIORITY)
**Concept:** Detect organized incoming swell lines in the offshore zone (200m-2km from shore), not just nearshore foam.

**Why it matters:** A headland with visible swell lines refracting around it + concentrated foam on the lee side = much stronger signal than random foam on a cliff. Swell lines are the parallel dark/light bands visible in RGB and NIR imagery.

**Approach options:**
- FFT (Fast Fourier Transform) on offshore pixels to detect periodic banding
- Edge detection (Canny/Sobel) on NIR imagery looking for parallel linear features
- Gradient analysis — swell lines create periodic intensity variations perpendicular to the coast
- Compare "organized" vs "chaotic" wave patterns (organized = surfable, chaotic = rocks/wind chop)

**Data needed:** Same Sentinel-2 scenes we already have, just analyze a wider buffer (200m-2km offshore instead of just 0-200m nearshore).

### 2. Foam Pattern Analysis
**Concept:** Not just "is there foam?" but "what does the foam look like?"

**Indicators of a surfable break:**
- Foam concentrated in a specific zone (not uniform along the whole segment)
- Arc or crescent-shaped foam patterns (classic beach break)
- Foam that tracks along a headland/reef line (point break signature)
- Clear transition from dark water → foam → white water → calm inside

**Indicators of rocks/cliffs:**
- Uniform foam along entire segment regardless of swell
- No clear "inside" calm zone
- Foam right at the cliff base with deep water immediately offshore

**Approach:** Spatial analysis of foam pixel distribution within the 200m buffer. Cluster analysis — is foam in one concentrated zone or spread everywhere?

### 3. Modular Scoring Weights (HIGH PRIORITY)
**Current:** Fixed 40/25/20/15 weights hardcoded in script 11.

**Proposed:** User-adjustable weight profiles:

```json
{
  "profile": "default",
  "weights": {
    "swell_exposure": 0.35,
    "geometry": 0.25,
    "bathymetry": 0.20,
    "road_access": 0.10,
    "satellite_evidence": 0.10
  }
}
```

**Preset profiles:**
- **Explorer** — road_access: 0, island_bonus: true. "Show me everything, I'll figure out access."
- **Accessible** — road_access: 0.25. "I need to be able to drive there."
- **Beginner** — gentle_bathymetry: high, moderate_swell_response: high. "Mellow waves please."
- **Advanced** — steep_bathymetry: high, large_swell_response: high. "Show me the heavy stuff."
- **Custom** — user adjusts sliders in the UI.

**Implementation:** Scoring function takes a weights dict. Web UI has slider controls. Server recalculates rankings on weight change (fast — it's just re-weighting pre-computed scores).

### 4. Break Type Classification
**Concept:** Estimate whether a candidate is a beach break, point break, reef break, or slab.

**Signals:**
- **Beach break:** Wide sandy coastline, foam across a broad zone, geometry score shows gentle gradient
- **Point break:** Headland geometry, foam concentrated on one side, swell refraction visible
- **Reef break:** Sharp bathymetric change, concentrated foam zone, exposed coastline
- **Slab:** Very steep bathymetric gradient, foam right at the rock edge

**Data sources:** Coastline geometry (already have), bathymetric gradient (GEBCO, partially implemented), foam distribution pattern (new).

### 5. Temporal Consistency
**Concept:** A real break shows up consistently across scenes with similar swell. Random foam doesn't.

**Approach:** For each segment, calculate the coefficient of variation of foam_fraction within each swell bin. Low variance = consistent breaking = likely real. High variance = inconsistent = possibly noise.

This is partially captured in swell profiles already but could be made more explicit as a confidence signal.

### 6. Multi-Resolution Analysis
**Concept:** Use both 10m (B8) and 20m (B11, B12) Sentinel-2 bands to separate wave foam from other bright surfaces.

**Why:** At 20m resolution, SWIR bands can help distinguish:
- Water foam (high NIR, moderate SWIR)
- Sand/rock (high NIR, high SWIR)
- Snow/ice (very high NIR, very high SWIR)

### 7. Tidal Influence
**Concept:** Some breaks only work on certain tides. Cross-reference scene timestamps with tide predictions.

**Data source:** NOAA/CHS tide stations near NS. Free data.

**Use:** "This segment shows foam primarily during low tide" = reef break that needs low tide to break.

## Manual Verification Protocol

Graham's ground truth verification is the most valuable near-term improvement.

### What to verify:
1. Look at satellite gallery images for each of the 16+ completed spots
2. For spots you know personally, rate:
   - Is this actually surfable? (yes / maybe / no / rocks/cliff)
   - Break type (beach / point / reef / slab / other)
   - Quality rating (1-5)
   - Best swell range (e.g., "works best 1-2m from the south")
   - Any notes ("only on low tide", "needs SE wind", "closeout on big days")
3. For spots you don't know, flag any obvious false positives from the imagery

### How this helps:
- Tune NIR threshold (800 might be too low/high)
- Validate swell-response profiles against local knowledge
- Identify which geometry factors actually predict good breaks
- Build training data for future ML classification
- Weight adjustments — if verified breaks cluster around certain geometry scores, we know the weights work (or need changing)

### Verification format:
```json
{
  "spot": "lawrencetown-beach",
  "segment_id": "ns-seg-03978",
  "verified": true,
  "surfable": "yes",
  "break_type": "beach",
  "quality": 4,
  "best_swell_range": "1.0-2.0m",
  "best_direction": "S/SE",
  "notes": "Main peak at the headland. Closes out over 2.5m. Works all tides but best mid.",
  "verified_by": "graham",
  "verified_date": "2026-03-26"
}
```

## Priority Order

1. **Modular weights** — quick win, huge UX improvement
2. **Manual verification** — ground truth makes everything better
3. **Foam pattern analysis** — concentrated vs dispersed foam
4. **Swell line detection** — harder but game-changing
5. **Break type classification** — combines geometry + pattern data
6. **Tidal influence** — adds dimension to profiles
7. **Multi-resolution** — more data, diminishing returns
