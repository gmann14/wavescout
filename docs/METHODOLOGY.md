# WaveScout Detection Methodology

*How we find surf spots from space — and what the data actually tells you.*

## The Short Version

WaveScout uses satellite imagery to detect foam/whitewater along coastlines, then combines that with coastline geometry and ocean data to identify segments that behave like surf breaks. It's evidence-based discovery, not wave forecasting.

**What it can tell you:** "This stretch of coast shows wave-breaking patterns consistent with a surfable break, especially in 1-1.5m S/SE swell."

**What it can't tell you:** "This is definitely a great wave." Only your feet in the water confirm that.

## Detection Pipeline

### Step 1: Coastline Segmentation
Nova Scotia's coastline is divided into ~16,939 segments (~500m each). Each segment gets scored on geometry alone:

| Factor | Weight | What It Measures |
|--------|--------|-----------------|
| Swell exposure | 40% | Does the segment face into the dominant Atlantic swell window (140-200°)? |
| Favorable geometry | 25% | Is it near a headland or in a bay? Headlands focus swell energy. |
| Bathymetric gradient | 20% | How quickly does the ocean floor shallow? Gradual = better wave formation. |
| Road access | 15% | Can you actually get there? |

Segments scoring above a threshold become candidates for satellite analysis.

### Step 2: NIR Foam Detection
We use Sentinel-2 satellite imagery (10m resolution, revisits every 5-12 days). The key is the near-infrared (NIR) band (B8):

- **Water absorbs NIR** → appears dark/black
- **Foam/whitewater reflects NIR** → appears bright white
- **Threshold:** B8 > 800 (calibrated against known breaks)

For each candidate segment, we analyze ~120 clear scenes (post-October 2021, <15% cloud cover) in a 200m nearshore buffer zone. Each observation records:
- `foam_fraction` — what percentage of nearshore pixels show foam
- `foam_extent_m` — estimated linear meters of active breaking
- Mean and max NIR values
- Paired marine conditions (swell height, period, direction from Open-Meteo)

### Step 3: Swell-Response Profiling
This is where a real break separates from just "ocean hitting rocks." By correlating foam detection with swell conditions across 120+ scenes, we build a profile:

- **Turn-on threshold** — minimum swell height where foam consistently appears (> 5% of pixels)
- **Optimal range** — swell height bin producing the most foam (the "sweet spot")
- **Blow-out point** — swell height where foam fraction exceeds 80% (likely closeouts or storm conditions)
- **Primary direction** — which swell direction produces the most breaking

### Step 4: Confidence Scoring
A segment's confidence level depends on multiple factors:

| Signal | High Confidence (Likely a Break) | Low Confidence (Might Be Rocks/Cliffs) |
|--------|----------------------------------|----------------------------------------|
| Swell response | Clear turn-on → optimal → blow-out curve | Constant foam at all swell heights |
| Geometry | Faces swell, gradual bathymetry | Steep cliff face, deep water right to shore |
| Foam pattern | Concentrated in specific zones | Uniform along entire segment |
| Direction sensitivity | Responds strongly to specific swell directions | Foams regardless of direction |

## Known Limitations

### What NIR Can't Distinguish
- **Cliffs vs beaches:** Rocky cliffs produce foam too. We mitigate this with geometry scoring (bathymetric gradient, favorable beach geometry) and swell-response profiles (cliffs foam at any swell, real breaks have a turn-on threshold).
- **Break quality:** A shore break on a steep beach and a perfect point break both show foam. The satellite can't tell you if it's hollow or mushy.
- **Tidal effects:** We don't currently factor in tide state. Some breaks only work on certain tides.
- **Wind effects:** Local wind chop can produce foam that looks like breaking waves.
- **Cloud cover:** We can only analyze clear scenes (<15% cloud). Winter storms are the ones producing the best swell, and they're often cloudy.

### Resolution Limits
Sentinel-2 is 10m/pixel. We can detect that *something is breaking* but can't see individual wave faces or determine wave height from the imagery.

### Temporal Gaps
Sentinel-2 revisits every 5-12 days. We might miss the best swells if they don't coincide with a clear satellite pass.

## How to Read the Evidence

### Satellite Image Gallery
Each spot shows 3-5 satellite images at different swell heights. You can toggle between:
- **True color (RGB)** — what it looks like to the human eye
- **NIR composite** — what the algorithm sees (water = black, foam = bright white)

Pin markers show where the algorithm detected the strongest foam signatures.

### Swell Profile Chart
Shows how foam fraction changes with swell height. A classic surfable break profile looks like:
```
Foam fraction
  ↑
  |         ████
  |       ████████
  |     ████████████
  |   ██████████████████
  | ██████████████████████████
  +---------------------------→ Swell height
  0   0.5   1.0   1.5   2.0+
      ↑           ↑
  turn-on      optimal
```

### What "Confirmed" vs "Candidate" Means
- **Confirmed:** Detected break matches a known surf spot (from WannaSurf, local knowledge, or community verification)
- **Candidate:** Satellite evidence suggests breaking waves, but no one has verified it's surfable
- **Rejected:** Community has verified this is rocks/cliffs/unsurfable

## Data Sources
- **Satellite imagery:** Copernicus Sentinel-2 (ESA), via Google Earth Engine
- **Marine conditions:** Open-Meteo Marine API (swell height, period, direction)
- **Bathymetry:** GEBCO (General Bathymetric Chart of the Oceans)
- **Coastline geometry:** OpenStreetMap
- **Known spots:** WannaSurf, local knowledge, community submissions
