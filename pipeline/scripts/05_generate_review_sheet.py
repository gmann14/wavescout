"""
Step 1.6: Generate an observation review sheet from scene inventory
and conditions manifests. Produces a CSV that a human fills in after
reviewing exported imagery.

The reviewer adds:
  - observation_label: present / none / unclear
  - notes: free text

Run examples:
    python3 pipeline/scripts/05_generate_review_sheet.py --spot lawrencetown-beach
    python3 pipeline/scripts/05_generate_review_sheet.py --all
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from _script_utils import default_manifest_path

MANIFESTS_DIR = Path("pipeline/data/manifests")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a CSV review sheet from scene inventory and conditions manifests."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--spot",
        help="Spot slug to generate review sheet for.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Generate review sheets for all spots with manifests.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("pipeline/data/reviews"),
        help="Output directory for CSV files. Default: pipeline/data/reviews",
    )
    return parser.parse_args()


def load_manifest(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def find_spot_slugs() -> list[str]:
    """Find all slugs that have a scene inventory manifest."""
    slugs = []
    for path in sorted(MANIFESTS_DIR.glob("*_scene_inventory.json")):
        slug = path.stem.replace("_scene_inventory", "")
        slugs.append(slug)
    return slugs


def build_review_rows(slug: str) -> list[dict]:
    """Join scene inventory dates with conditions data into review rows."""
    inventory = load_manifest(default_manifest_path("scene_inventory", slug))
    conditions = load_manifest(default_manifest_path("conditions_manifest", slug))

    if inventory is None:
        print(f"  No scene inventory for {slug}, skipping")
        return []

    # Index conditions by date
    cond_by_date = {}
    if conditions is not None:
        for obs in conditions.get("observations", []):
            cond_by_date[obs["date"]] = obs

    spot_name = inventory.get("region", {}).get("name", slug)
    dates = inventory.get("clear_scene_dates", [])

    rows = []
    for date in dates:
        cond = cond_by_date.get(date, {})
        marine = cond.get("marine", {})
        weather = cond.get("weather", {})

        rows.append({
            "spot": spot_name,
            "slug": slug,
            "date": date,
            "wave_height_m": marine.get("wave_height_m"),
            "wave_direction_deg": marine.get("wave_direction_deg"),
            "wave_period_s": marine.get("wave_period_s"),
            "swell_height_m": marine.get("swell_height_m"),
            "swell_direction_deg": marine.get("swell_direction_deg"),
            "swell_period_s": marine.get("swell_period_s"),
            "wind_speed_kmh": weather.get("wind_speed_kmh"),
            "wind_direction_deg": weather.get("wind_direction_deg"),
            "wind_gusts_kmh": weather.get("wind_gusts_kmh"),
            # Reviewer fills these in:
            "observation_label": "",
            "notes": "",
        })

    return rows


FIELDNAMES = [
    "spot",
    "slug",
    "date",
    "wave_height_m",
    "wave_direction_deg",
    "wave_period_s",
    "swell_height_m",
    "swell_direction_deg",
    "swell_period_s",
    "wind_speed_kmh",
    "wind_direction_deg",
    "wind_gusts_kmh",
    "observation_label",
    "notes",
]


def write_review_csv(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()

    if args.all:
        slugs = find_spot_slugs()
        if not slugs:
            print("No scene inventory manifests found. Run 01_test_gee_access.py first.")
            return
    else:
        slugs = [args.spot]

    for slug in slugs:
        rows = build_review_rows(slug)
        if not rows:
            continue

        output_path = args.output_dir / f"{slug}_review.csv"
        write_review_csv(rows, output_path)
        print(f"Review sheet: {output_path} ({len(rows)} observations)")

    print("\nInstructions:")
    print("  1. Open the CSV and review the exported imagery for each date")
    print("  2. Set observation_label to: present / none / unclear")
    print("  3. Add any notes about what you see")
    print("  4. Save the CSV — it feeds into the feasibility decision")


if __name__ == "__main__":
    main()
