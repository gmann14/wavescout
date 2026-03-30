# Spec: NS Coastline Satellite Atlas

> Tile the entire southern Nova Scotia coastline into browsable sections with 10-15 satellite images each at varying swell conditions, for manual surf spot discovery.

## Problem

We have gallery images for 41 known spots, but there's potentially 1000+ km of coastline with undiscovered breaks. A human (Graham) can identify surf breaks visually at 10m/pixel — but needs a systematic way to browse the entire coast under different swell conditions.

## Coastline Scope

### What to cover

**Southern/Eastern exposed coast** — from Yarmouth (west) around to Cape Breton (northeast). This is the swell-exposed Atlantic coast.

Rough extent: `(-66.4, 43.3)` to `(-59.7, 46.9)` — but only the ocean-facing segments, not inland bays or the Northumberland Strait side (no significant swell).

### Length estimate

We already have 16,939 exposed coastline segments from `10_segment_coastline.py` (500m segments, 250m stride, filtered by exposure arc). At 500m per segment, that's ~8,470km of raw exposed coastline — but with 250m overlap, unique coverage is roughly **4,200km**.

For gallery tiling, we want larger sections (~3km each) = **~1,400 sections** if covering all exposed coast, or **~300-500 sections** if filtering to south/east facing with decent geometry scores.

## Tiling Strategy

### Option A: Segment-based tiling (leverage existing data)

Use the scored segments from `11_score_geometry.py` to create tiles:

1. **Group segments into ~3km sections** along the coastline
2. **Score sections** by max segment geometry score within them
3. **Prioritize higher-scored sections** for gallery generation
4. **Generate images for all sections** but order/highlight by score

Implementation:
```python
# Group consecutive segments into sections
sections = []
current_section = [segments[0]]
for seg in segments[1:]:
    if distance(current_section[-1], seg) < 500:  # consecutive
        current_section.append(seg)
        if section_length(current_section) >= 3000:  # 3km
            sections.append(current_section)
            current_section = []
    else:
        sections.append(current_section)  # gap = new section
        current_section = [seg]
```

Each section gets a bbox derived from its constituent segments, plus a buffer for context.

### Option B: Fixed-grid tiling

Divide the coast into a regular grid of ~3km × 3km tiles, filter to those that intersect the coastline.

Simpler but wasteful — many tiles would be mostly ocean or mostly land.

**Recommendation:** Option A — leverages existing segment data and naturally follows the coastline.

## Gallery Generation per Section

Reuse `16_generate_gallery_fast.py` logic:

1. **Scene dates:** Query GEE for clear scenes within section bbox (same as spots)
2. **Conditions:** Batch Open-Meteo lookup for swell height/period/direction
3. **Quality:** SCL quality check for top candidates per swell bin
4. **Selection:** Pick 10-15 scenes across swell bins (expanded from 12 bins, allow multiple per bin)
5. **Export:** RGB + NIR thumbnails at 800px width
6. **Tide:** CHS API lookup (nearest station)

### Scaling considerations

- **300-500 sections × ~90s each = 7.5-12.5 hours** for full coast
- Can be parallelized: GEE supports concurrent requests
- Can be incremental: generate sections on-demand as user browses
- **Storage:** ~500 sections × 12 scenes × 2 images × 200KB = ~2.4GB
- Start with a subset (top 100 scored sections) to validate the approach

## UI Design

### Map-driven browsing

```
┌─────────────────────────────────────┐
│  [Map view - full NS coast]         │
│                                     │
│  ████████ ← coastline sections      │
│  ████  colored by:                  │
│  ████    - geometry score           │
│  ████    - known spot (teal pin)    │
│                                     │
│  Click section → gallery panel      │
│                                     │
├─────────────────────────────────────┤
│  Section: "Cape Forchu - 3.2km"     │
│  Score: 72/100 | Exposure: S-SW     │
│  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐    │
│  │0.3│ │0.8│ │1.2│ │1.8│ │3.5│    │
│  │ m │ │ m │ │ m │ │ m │ │ m │    │
│  └───┘ └───┘ └───┘ └───┘ └───┘    │
│  ← swipe for more scenes →         │
│                                     │
│  [Flag as potential break] [Skip]   │
└─────────────────────────────────────┘
```

### Key UI features

1. **Section highlights on map** — colored polylines along coastline, click to expand
2. **Known spots overlay** — teal pins for existing 41 spots, clearly visible on top of sections
3. **Gallery panel** — same component as current spot gallery, but for sections
4. **Navigation** — "Next section" / "Previous section" buttons for sequential browsing
5. **Labeling UI** — "Flag as potential break" button that saves coordinates + notes
6. **Filter controls** — filter sections by geometry score, exposure direction, region

### Data model

```typescript
interface CoastSection {
  id: string;              // e.g. "section-0042"
  name: string;            // auto-generated: "Cape Forchu Area"
  bbox: [number, number, number, number];
  geometry_score: number;  // max segment score in section
  exposure_deg: number;    // dominant exposure direction
  length_km: number;
  segment_ids: string[];   // constituent segment IDs
  nearest_spot?: string;   // slug of nearest known spot
  scenes: GalleryScene[];  // same schema as spot galleries
  flags: BreakFlag[];      // user annotations
}

interface BreakFlag {
  lat: number;
  lon: number;
  note: string;
  flagged_at: string;
  swell_at_flag: number;   // what swell was showing when flagged
}
```

## Phased Rollout

### Phase 1: Section generation (backend)
- Build section grouping from existing segments
- Generate gallery for top 50-100 sections (highest geometry score)
- ~2-3 hours processing time
- Output: sections manifest + images

### Phase 2: Basic browser (frontend)
- Map with section highlights (colored by score)
- Click section → gallery panel (reuse ImageGallery component)
- Known spot pins visible alongside section highlights
- Sequential navigation between sections

### Phase 3: Labeling + discovery
- "Flag potential break" button with coordinate picker
- Notes field for each flag
- Export flagged locations for investigation
- Compare flagged sections across swell conditions

### Phase 4: Full coast coverage
- Generate remaining sections (all exposed coastline)
- Incremental generation: only re-process sections that need updates
- Progressive loading in UI (load images on scroll/click)

## Effort Estimate

| Phase | Backend | Frontend | Total |
|-------|---------|----------|-------|
| 1     | 3-4h    | —        | 3-4h  |
| 2     | 1h      | 4-6h     | 5-7h  |
| 3     | 1h      | 2-3h     | 3-4h  |
| 4     | 2h      | 1h       | 3h    |
| **Total** | **7-8h** | **7-10h** | **14-18h** |

Phase 1+2 are the MVP — browsable coastline atlas with ~50-100 sections.

## Dependencies

- Existing segment data from `10_segment_coastline.py` + `11_score_geometry.py`
- `16_generate_gallery_fast.py` (gallery generation engine)
- Mapbox GL JS (already in web viewer)
- GEE quota (should be fine — same as current pipeline)

## Open Questions

1. **Section naming:** Auto-generate from nearest place name? Or just "Section 42"?
2. **Overlap between sections and spot galleries:** Show both? Or merge when a section contains a known spot?
3. **Storage/hosting:** 2.4GB of images for full coast — fine for local dev, but needs CDN for production
4. **Processing priority:** Start with south shore (most surfable) or do full coast?
