# Spot Validation Log

> Manual validation notes from Graham reviewing satellite gallery images.
> Used to calibrate the foam detection algorithm and swell response profiles.

---

## Snapjaw (graham-local-knowledge, point break)

**Date reviewed:** 2026-03-26
**Reviewer:** Graham Mann

### Observations:
- **Cloud cover contamination:** Some gallery images have cloud cover that likely inflates foam fraction. Need cloud masking (SCL band) before foam detection.
- **High swell threshold:** Only shows meaningful foam at 3.4m+ swell. At 0.4m, 0.7m, 1.2m, 1.9m — minimal to no visible break activity. This is characteristic of a point break that needs significant energy to activate.
- **Not tide-dependent:** No visible tidal effect on break quality. Foam patterns similar regardless of tide state.
- **Foam signature is subtle:** Even at 3.4m swell, Snapjaw shows the least obvious foam in the image compared to adjacent beach breaks. Point breaks concentrate energy in a narrower zone vs long shoreline foam on beaches.
- **Swell lines visible:** At 3.4m, clear wave train striations visible approaching from SE.

### Algorithm Implications:
- Cloud masking is mandatory before foam fraction calculation
- Point breaks need different foam thresholds than beach breaks (lower foam % can still indicate active breaking)
- Swell turn-on threshold for Snapjaw: ~3.0m+ (high for NS)
- Consider break type (point vs beach vs reef) as a weighting factor in scoring

---

---

## Hell Point (graham-local-knowledge, beach/headland break)

**Date reviewed:** 2026-03-26
**Reviewer:** Graham Mann

### Observations:
- **Cloud cover contamination (critical):** 2024-06-21 shows 73% foam at 0.4m swell — entirely clouds. Cloud masking is mandatory.
- **1.7m SE swell (118°, 9.3s period) shows promise:** Clean groundswell wrapping around headland, visible shoreline foam. 14% foam fraction is realistic for this spot.
- **Swell direction matters:** SSW swells (200°) don't seem to produce breaking waves here. SE swells do. This spot likely needs specific swell window exposure.
- **Tide: unclear effect** — not enough clean (cloud-free) data points to assess tidal dependency.

### Algorithm Implications:
- Cloud masking before foam detection (reinforces Snapjaw finding)
- Swell direction should be a factor in spot scoring — some spots only work on specific windows
- Need to display swell direction + period in gallery (data exists, just not shown)
- Consider adding cloud cover % to gallery metadata as data quality indicator

---

## Hirtle's Beach (graham-local-knowledge, beach break)

**Date reviewed:** 2026-03-26
**Reviewer:** Graham Mann

### Observations:
- **Cloud contamination:** Same issue as other spots — clouds inflating foam %.
- **SNOW contamination (new issue):** 2026-03-10 image shows heavy snow cover on land. Snow reflects high NIR just like foam. If snow within the water buffer zone, it inflates foam fraction. 63% foam at 1.0m swell is clearly wrong.
- **Beach break visible:** Even in the snowy image, you can see the characteristic crescent beach break pattern in the water. The break is there, but the numbers are garbage.
- **Tide data looks right:** Low tide (0.8m) with exposed sand — checks out visually.

### Algorithm Implications:
- **SCL (Scene Classification Layer) masking is mandatory** — must filter clouds AND snow before foam detection
- Winter scenes (Nov-Apr) are especially unreliable without SCL masking
- Consider seasonal flagging: winter scenes should carry a "low confidence" tag unless SCL-clean
- Add data quality metric: % of buffer zone that's clean (no cloud, no snow, no shadow)
- Three contamination sources now identified: clouds, snow, cloud shadows
- **Clean scene baseline (2022-09-10):** 1.7m swell, high tide (1.9m), 57% foam — this is a LEGIT reading. Shows continuous foam band along beach with distinct A-frame peaks visible. Use as reference for what clean data looks like.
- Beach break signature: continuous foam band along shoreline (vs point break narrow zone)
- Works at high tide — no shallow sandbar cutoff
- Good methodology page candidate image

---

## Gaff Point (graham-local-knowledge, headland/uncertain)

**Date reviewed:** 2026-03-26
**Reviewer:** Graham Mann

### Observations:
- **Cliff foam dominates:** 2023-09-05 (1.9m, 113° ESE, 9.2s) shows continuous white foam wrapping the entire rocky headland. This is wave energy hitting cliffs, not a surfable break.
- **Adjacent beach break visible:** Northern foam band is actually Hirtle's Beach, not Gaff Point. Need cleaner spatial separation.
- **Uncertain break:** Graham has "heard of" a wave here but hasn't confirmed. May need very specific swell direction (S/SSW?) to wrap around the point and create a surfable break vs just cliff impact.
- **Swath edge issue:** Scene 5/5 (2023-11-19) broken — same orbit boundary as Hirtle's.
- **Low tide (0.5m) on this scene** — tide data looks correct.

### Algorithm Implications:
- **Cliff foam filter needed:** Foam along steep rocky coastline (headlands, cliffs) should be classified differently from beach foam. Could use DEM/slope data or coastline type classification.
- **Spatial separation:** When two spots are close (Gaff Point + Hirtle's), their foam buffers may overlap. Need per-spot masking that excludes adjacent spot zones.
- **Swell window hypothesis:** Gaff Point may only produce surfable waves from specific directions (S/SSW?). Current ESE swell just creates cliff impact. Swell direction filtering per-spot could improve scoring.
- "Heard of a wave" status = Tier 2 candidate, not confirmed

---

## Cherry Hill (well-known, beach break)

**Date reviewed:** 2026-03-26
**Reviewer:** Graham Mann

### Observations:
- **Snow contamination:** Scene 1/4 (2026-03-10, 0.3m swell) = 80% foam — entirely snow. Worst contamination example yet.
- **Cloud contamination:** Scene 2/4 (2024-09-29, 0.9m swell) = 96% foam — partial cloud.
- **No A-frame pattern in clean scenes:** Even clean images (3/4, 4/4) show uniform shore-break foam along the crescent beach, not distinct A-frame peaks.
- **Swell direction effect:** 86° E (6.7s) produces uniform shore-break. May need SE swell (100-140°, 8s+) for A-frame formation.
- **Low tide sand exposure:** Scene 3/4 (low tide 0.6m) shows bright exposed sand that likely inflates foam %. Wet sand reflects bright in satellite imagery.
- **64% foam at 1.4m swell is likely inflated** by exposed low-tide sand, not all actual wave foam.

### Algorithm Implications:
- **Low tide sand exposure = false foam** — water mask must account for tidal sand changes. At low tide on crescent beaches, the exposed sand boundary shifts significantly.
- Contamination source #4 identified: bright wet/dry sand at low tide
- Full contamination list: clouds, snow, swath edges, low-tide sand exposure
- Cherry Hill may need mid-tide + higher swell + longer period SE to produce quality waves
- Crescent beach geometry: uniform exposure → uniform foam band (vs headland refraction creating peaks)
- **DISCOVERY: Possible right-hand point break on SW headland.** Scene 4/4 (2026-03-18, 1.8m swell, high tide) shows swell lines wrapping around the rocky headland with concentrated foam zone. Classic point break refraction pattern. Beach blown out at this swell/tide but headland organizing waves into cleaner break. Worth investigating as separate spot.
- Wide satellite view crucial for this kind of discovery — wouldn't see the refraction pattern in a cropped view

---

## Seaside (graham-local-knowledge, coastal/sheltered)

**Date reviewed:** 2026-03-26
**Reviewer:** Graham Mann

### Observations:
- **100% foam at 0.4m = cloud contamination.** Right half of image entirely cloud. Most extreme false reading yet.
- **3.2m SSE swell (161°, 11.1s) shows some foam at 9%.** Clean scene, foam visible along outer coast (bottom-right). Inner harbour/lagoon completely calm — good contrast.
- **High swell threshold:** Needs 3m+ to show any foam. Sheltered by lagoon/harbour geography.
- **Outer coast vs inner harbour:** The surf zone is the exposed Atlantic-facing rocky coast, not the sheltered bay. Spot may need repositioning to focus on the outer headland.
- **Swell direction important:** SSE (161°) works. SSW (200°) at 0.4m obviously too small to judge.

### Algorithm Implications:
- Reinforces cloud masking requirement
- Sheltered spots have very different foam characteristics — high swell threshold, low foam fraction even when active
- Consider "exposure classification" for spots: fully exposed vs partially sheltered vs harbour
- Lagoon/harbour areas within spot buffer may need exclusion from foam calculation

---

## Lawrencetown Beach (well-known, beach break complex)

**Date reviewed:** 2026-03-26
**Reviewer:** Graham Mann

### Observations:
- **Bbox too wide (0.10°)** — images way too zoomed out vs other spots. Tighten to ~0.05°. But wide view does show the full barrier beach system.
- **Scene 2/5 (99% foam, 0.6m):** Entire image through cloud/haze layer. Total washout.
- **Scene 3/5 (75% foam, 1.0m):** Heavy snow but break profiles visible through the contamination. Foam line along shoreline is legit. Beach fires at lower swell than south shore spots.
- **Scene 4/5:** Good profiles visible, starting to blow out at many spots, clear wave lines approaching shore.
- **Scene 5/5 (97% foam, 3.7m, low tide):** Stunning. Multiple distinct foam zones, clear offshore wave patterns (curved swell lines), rip currents visible, barrier beach/lagoon system clear. 97% foam may be close to real at this swell size + low tide sand exposure.
- **Multiple break zones:** Lawrencetown is really several spots along a barrier beach — different sections respond differently to same swell.
- **Lower activation threshold** than south shore spots — visible foam at 1.0m.
- **Coordinate needs repositioning** + tighter bbox

### Algorithm Implications:
- Long barrier beaches could be treated as multi-zone spots — different scoring per section
- Lower foam threshold for east coast vs south coast NS (different exposure)
- Wide view valuable for understanding beach system context even if per-spot view should be tighter
- Haze/thin cloud (not just thick cloud) needs SCL detection

---

## Cow Bay (well-known, cove/beach break)

**Date reviewed:** 2026-03-26
**Reviewer:** Graham Mann

### Observations:
- **Location uncertain** — Graham not 100% sure of exact placement, but looks like a legit surf spot from satellite
- **Scene 3/5 (100% foam, 1.0m):** Pure snow. Entire coastline white.
- **Scene 4/5 (19% foam, 2.3m, SSE 171°, 9.4s):** Excellent. Clean skies, strong foam line along crescent beach, wave lines approaching from SE, headland creating shadow zone. Wedge/peak visible at beach-headland junction.
- **Cove geometry creates wave focus** — swell wraps around headland and converges in bay
- **19% foam at 2.3m is credible** for a partially sheltered cove — not every pixel is breaking, just the active surf zone
- **SSE swell (171-176°) works well** for this south-facing cove

### Algorithm Implications:
- Cove breaks have naturally lower foam % than open beach — don't penalize in scoring
- Headland-beach junction peaks could be detected as concentrated foam zones (vs diffuse beach foam)
- Good example of realistic foam readings on clean scenes

---

*Add more spots below as validation continues.*
