# WaveScout Product Vision

*Updated: March 25, 2026*

## Core Mission
Find surf spots that MIGHT work based on satellite imagery, coastline geometry, and bathymetry data. The original goal: identify candidate spots in Nova Scotia, then expand to anywhere.

## Target Users
- NS surfers exploring beyond the known breaks
- Traveling surfers researching unfamiliar coastlines
- Surf explorers who want evidence, not just word-of-mouth

## Feature Map

### 1. Spot Database (WannaSurf but better)
- List all known spots with conditions, break type, swell direction, experience level
- Rich filtering: by break type, swell direction, size range, experience level, distance
- Community data: photos, comments, local knowledge summaries
- Source: WannaSurf scrape + Surfline + Stormrider + local knowledge + user submissions

### 2. Spot Finder (core differentiator)
- "Find spots near me that might work"
- Uses satellite-detected foam evidence + coastline geometry + bathymetry scoring
- Per-segment swell-response profiles: turn-on threshold, optimal range, blow-out point
- Suggestions ranked by evidence strength with uncertainty shown
- Works NS first, expandable to any coastline with Sentinel-2 coverage

### 3. Satellite Evidence Viewer
- View satellite imagery of any spot under different conditions
- Compare flat day vs swell day (NIR band shows foam as bright white)
- Historical evidence browser: "this segment showed foam on X dates"
- Educational: help people understand what the data shows

### 4. Conditions Integration (Phase 5+)
- Match good spots with current/forecast swell + wind + tide
- "These spots should be working right now" based on profiles
- Not a forecasting tool — a discovery tool that shows when to check

### 5. Community
- Submit new spots
- Upload photos with conditions
- Comments and local knowledge
- Verify/correct satellite detections ("yes this breaks" / "no this is just whitewater on rocks")
- Rate spots

## Design Principles
- Mobile-first (surfers check on their phones)
- Evidence-first: show why a segment is ranked, don't hide behind scores
- Fast and intuitive
- Beautiful map-centric UI
- Start NS, design for global

## Data Pipeline
1. Coastline segmentation (16,939 NS segments scored)
2. NIR foam detection across time series (120 scenes per spot)
3. Swell-response profile generation per segment
4. Cross-validation with known spot data (WannaSurf, local knowledge)
5. Confidence scoring: geometry + satellite evidence + community confirmation

## What Makes This Different
- WannaSurf/Surfline only list KNOWN spots submitted by users
- WaveScout discovers CANDIDATE spots from satellite evidence
- Shows the "why" with real data, not just "trust me bro"
- Evidence is reproducible and traceable to specific scenes/dates
