#!/bin/bash
# Run foam detection + swell profiles for all remaining spots
set -e
cd "$(dirname "$0")/../.."

SCRIPTS="pipeline/scripts"
MANIFESTS="pipeline/data/manifests"

SPOTS=(
  hell-point
  hirtles-beach
  gaff-point
  seaside
  white-point
  western-head
  cherry-hill
  point-michaud
  clam-harbour
  summerville
  kennington-cove
  ingonish
  mavillette
  broad-cove
  gullivers-cove
)

for spot in "${SPOTS[@]}"; do
  config="pipeline/configs/${spot}.json"
  foam_out="${MANIFESTS}/${spot}_foam_detections.json"
  profile_out="${MANIFESTS}/${spot}_swell_profiles.json"

  if [ -f "$foam_out" ] && [ -f "$profile_out" ]; then
    echo "⏭️  $spot — already complete, skipping"
    continue
  fi

  echo ""
  echo "🌊 [$spot] Starting foam detection..."
  if [ ! -f "$foam_out" ]; then
    python3 "$SCRIPTS/13_detect_foam_nir.py" --config "$config" || {
      echo "❌ [$spot] Foam detection FAILED — continuing to next"
      continue
    }
  else
    echo "  ✅ Foam detections exist, skipping to profiles"
  fi

  echo "📊 [$spot] Building swell profiles..."
  python3 "$SCRIPTS/14_build_swell_profiles.py" --input "$foam_out" || {
    echo "❌ [$spot] Profile build FAILED — continuing to next"
    continue
  }

  echo "✅ [$spot] COMPLETE"
done

echo ""
echo "🏁 ALL SPOTS PROCESSED"
echo "Completed: $(ls ${MANIFESTS}/*_swell_profiles.json 2>/dev/null | wc -l) / 20 profiles"
