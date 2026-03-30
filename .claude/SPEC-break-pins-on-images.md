# Spec: Break Pins on Satellite Images

> Overlay surf break markers on gallery satellite images so viewers can see exactly where the breaks are.

## Problem

Gallery images show coastline at 10m/pixel but there's no indication of where the actual surf breaks are. A viewer unfamiliar with the area can't tell which part of the image is the surf spot. Even experienced surfers benefit from seeing exactly where multiple breaks sit relative to each other (e.g. The Moose vs Osbourne vs Minutes are all visible in the same Sentinel-2 tile).

## Approach

### Option A: Server-side rendering (Python/PIL) — Recommended

Add break pin overlay during image generation in `16_generate_gallery_fast.py`:

1. **Input:** spot config has `point: {lat, lon}` for the primary break. For multi-break spots (e.g. Cow Bay area), add a `breaks` array to the config:
   ```json
   {
     "breaks": [
       {"name": "The Moose", "lat": 44.61383, "lon": -63.43175, "type": "reef"},
       {"name": "Osbourne", "lat": 44.61774, "lon": -63.417031, "type": "point"}
     ]
   }
   ```

2. **Coordinate → pixel mapping:** The bbox defines the geographic extent, IMAGE_WIDTH=800 defines pixel width. Simple linear interpolation:
   ```python
   px_x = int((lon - bbox_west) / (bbox_east - bbox_west) * img_width)
   px_y = int((bbox_north - lat) / (bbox_north - bbox_south) * img_height)
   ```

3. **Rendering:** After downloading the PNG from GEE, use Pillow to draw:
   - Small circle marker (5-8px radius, teal with white border)
   - Optional label text (break name, small font, with shadow for readability)
   - Different marker colors by break type (reef=teal, point=orange, beach=yellow)

4. **Save as separate file** (`_annotated.png`) so raw images remain available:
   ```
   lawrencetown_2022-09-10_1.6m_rgb.png           # clean
   lawrencetown_2022-09-10_1.6m_rgb_annotated.png  # with pins
   ```

5. **Web viewer toggle:** Add a "Show breaks" toggle in the gallery UI that switches between clean and annotated images.

### Option B: Client-side overlay (CSS/Canvas)

Render pins in the browser on top of images. More flexible (interactive tooltips, hover effects) but requires:
- Passing break coordinates + bbox to the frontend
- Canvas overlay or absolute-positioned markers
- Correct scaling at different viewport sizes

**Recommendation:** Start with Option A (simpler, works in lightbox), add Option B later for interactive features.

## Implementation Steps

1. **Add `breaks` field to spot configs** that have multiple breaks (most have just one `point`)
2. **Add `pillow` to venv** (`pip install Pillow`)
3. **Add `annotate_image()` function** to script 16:
   - Takes image bytes, bbox, list of break coords
   - Returns annotated image bytes
4. **Generate both clean and annotated PNGs** per scene
5. **Update manifest** with `annotated_rgb_path` field
6. **Update ImageGallery.tsx** with toggle between clean/annotated

## Data Requirements

- Every spot config already has a `point` field (primary break location)
- Multi-break spots need `breaks` array added to config
- Known multi-break areas:
  - Cow Bay: The Moose, Osbourne, Minutes (3 breaks)
  - Lawrencetown: Beach, Point, Left Point, Right Point (4 breaks, separate configs but overlap in imagery)
  - Broad Cove area: Broad Cove, Artie's, Bullfield (3 breaks)

## Effort Estimate

- Config updates: 30 min
- Python annotation function: 1-2 hours
- Web toggle: 30 min
- Total: ~3 hours

## Dependencies

- `Pillow` Python package
- Break coordinates for all spots (mostly already in configs)
