#!/bin/bash
# WaveScout Overnight Pipeline — Mar 27 2026
# Runs AFTER foam detection completes (which is already running in another tmux)
# Steps: swell profiles → gallery → web data build
set -euo pipefail

cd ~/Coding/wavescout
source venv/bin/activate

LOG="pipeline/logs/overnight_$(date +%Y%m%d_%H%M%S).log"
mkdir -p pipeline/logs

echo "=== WaveScout Overnight Run (post-foam) ===" | tee "$LOG"
echo "Started: $(date)" | tee -a "$LOG"

# Step 1: Build swell profiles for all spots
echo "" | tee -a "$LOG"
echo "=== STEP 1: Swell Profiles (all spots) ===" | tee -a "$LOG"
python3 -u pipeline/scripts/14_build_swell_profiles.py --all-spots 2>&1 | tee -a "$LOG"

# Step 2: Gallery generation for all spots
echo "" | tee -a "$LOG"
echo "=== STEP 2: Gallery Generation (all spots) ===" | tee -a "$LOG"
python3 -u pipeline/scripts/15_generate_gallery_images.py --all-spots 2>&1 | tee -a "$LOG"

# Step 3: Build web data bundle
echo "" | tee -a "$LOG"
echo "=== STEP 3: Web Data Build ===" | tee -a "$LOG"
python3 -u pipeline/scripts/build_web_data.py 2>&1 | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== COMPLETE ===" | tee -a "$LOG"
echo "Finished: $(date)" | tee -a "$LOG"
echo "Log: $LOG"
