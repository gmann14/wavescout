#!/bin/bash
# Full gallery pipeline: foam detection for missing spots → gallery regen → sync to web
# Run from wavescout root: ./pipeline/scripts/run_full_gallery_pipeline.sh

set -e
cd "$(dirname "$0")/../.."

VENV="./venv/bin/python3"
LOG="/tmp/gallery-pipeline-$(date +%Y%m%d-%H%M).log"

echo "=== WaveScout Full Gallery Pipeline ===" | tee "$LOG"
echo "Started: $(date)" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Phase 1: Foam detection for spots missing data
echo "=== PHASE 1: Foam detection for missing spots ===" | tee -a "$LOG"
MISSING_FOAM=(the-cove eastern-brook juicys pubnico-beach the-juice the-meadows)
for slug in "${MISSING_FOAM[@]}"; do
    echo "" | tee -a "$LOG"
    echo "--- Processing $slug ---" | tee -a "$LOG"
    $VENV pipeline/scripts/13_detect_foam_nir.py \
        --config "pipeline/configs/$slug.json" \
        --limit 200 2>&1 | tee -a "$LOG"
done

# Phase 2: Full gallery regeneration
echo "" | tee -a "$LOG"
echo "=== PHASE 2: Gallery regeneration (all spots) ===" | tee -a "$LOG"
$VENV pipeline/scripts/15_generate_gallery_images.py --all 2>&1 | tee -a "$LOG"

# Phase 3: Remove Forevers from gallery
echo "" | tee -a "$LOG"
echo "=== PHASE 3: Cleanup ===" | tee -a "$LOG"
if [ -d "pipeline/data/gallery/forevers" ]; then
    rm -rf "pipeline/data/gallery/forevers"
    echo "Removed forevers from gallery" | tee -a "$LOG"
fi

# Phase 4: Sync to web viewer
echo "" | tee -a "$LOG"
echo "=== PHASE 4: Sync to web viewer ===" | tee -a "$LOG"

# Update gallery.json with web-friendly paths
$VENV -c "
import json
m = json.load(open('pipeline/data/gallery/manifest.json'))
# Remove forevers
m['spots'] = [s for s in m['spots'] if s['slug'] != 'forevers']
for spot in m['spots']:
    for scene in spot['scenes']:
        for key in ['rgb_path', 'nir_path']:
            if key in scene:
                scene[key] = scene[key].replace('pipeline/data/gallery/', '/data/gallery/')
json.dump(m, open('web/public/data/gallery.json', 'w'), indent=2)
json.dump(m, open('web/public/data/gallery/manifest.json', 'w'), indent=2)
print(f'Updated gallery.json: {len(m[\"spots\"])} spots, {sum(len(s[\"scenes\"]) for s in m[\"spots\"])} scenes')
"

# Sync gallery images
rsync -av --delete pipeline/data/gallery/ web/public/data/gallery/ \
    --exclude=manifest.json --exclude=forevers 2>&1 | tail -3

echo "" | tee -a "$LOG"
echo "=== COMPLETE ===" | tee -a "$LOG"
echo "Finished: $(date)" | tee -a "$LOG"
echo "Log: $LOG"
