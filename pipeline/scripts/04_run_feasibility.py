"""
Step 1.5: Run the feasibility pipeline across multiple known spots.

Orchestrates scene inventory (01) and conditions lookup (03) for each
configured spot. Image export (02) is skipped by default since it requires
manual review and Drive quota — use --export to include it.

Run examples:
    python3 pipeline/scripts/04_run_feasibility.py
    python3 pipeline/scripts/04_run_feasibility.py --spots lawrencetown cow-bay martinique-beach
    python3 pipeline/scripts/04_run_feasibility.py --export
    python3 pipeline/scripts/04_run_feasibility.py --spots-dir pipeline/configs
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _script_utils import (
    build_run_manifest,
    default_manifest_path,
    generate_run_id,
    load_region_config,
    write_json,
)

CONFIGS_DIR = Path(__file__).resolve().parents[1] / "configs"
SCRIPTS_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Phase 1 feasibility pipeline across multiple spots. "
            "Executes scene inventory and conditions lookup for each config."
        )
    )
    parser.add_argument(
        "--spots",
        nargs="*",
        help=(
            "Spot slugs to process (match config filenames without .json). "
            "Default: all JSON files in the configs directory."
        ),
    )
    parser.add_argument(
        "--spots-dir",
        type=Path,
        default=CONFIGS_DIR,
        help=f"Directory containing spot config files. Default: {CONFIGS_DIR}",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Also run image export (02). Requires GEE Drive access.",
    )
    parser.add_argument(
        "--cloud-max",
        type=float,
        default=30.0,
        help="Max cloud percentage for scene inventory. Default: 30",
    )
    parser.add_argument(
        "--conditions-limit",
        type=int,
        default=20,
        help="Max dates to check conditions for per spot. Default: 20",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Path for the combined feasibility manifest.",
    )
    parser.add_argument(
        "--project",
        help="GEE cloud project ID. Default: GEE_PROJECT env var.",
    )
    return parser.parse_args()


def discover_configs(spots_dir: Path, slugs: list[str] | None) -> list[Path]:
    """Find config files, optionally filtered to specific slugs."""
    all_configs = sorted(spots_dir.glob("*.json"))
    if not all_configs:
        raise FileNotFoundError(f"No config files found in {spots_dir}")

    if slugs is None:
        return all_configs

    found = []
    for slug in slugs:
        path = spots_dir / f"{slug}.json"
        if not path.exists():
            # Try matching with the slug as part of filename
            matches = [c for c in all_configs if slug in c.stem]
            if matches:
                found.append(matches[0])
            else:
                print(f"Warning: no config found for slug '{slug}', skipping")
        else:
            found.append(path)
    return found


def run_script(script_name: str, config_path: Path, extra_args: list[str] | None = None) -> bool:
    """Run a pipeline script as a subprocess. Returns True on success."""
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / script_name),
        "--config", str(config_path),
    ]
    if extra_args:
        cmd.extend(extra_args)

    print(f"  Running: {script_name}")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main() -> None:
    args = parse_args()
    configs = discover_configs(args.spots_dir, args.spots)

    print(f"Feasibility pipeline: {len(configs)} spot(s)")
    print(f"Configs: {[c.stem for c in configs]}\n")

    # Build project args to pass through to GEE scripts
    project_args = ["--project", args.project] if args.project else []

    results = []

    for config_path in configs:
        config = load_region_config(config_path)
        slug = config["slug"]
        print(f"\n{'='*60}")
        print(f"Processing: {config['name']} ({slug})")
        print(f"{'='*60}")

        spot_result = {
            "slug": slug,
            "config_path": str(config_path),
            "steps": {},
        }

        # Step 1: Scene inventory
        inventory_ok = run_script(
            "01_test_gee_access.py",
            config_path,
            ["--cloud-max", str(args.cloud_max)] + project_args,
        )
        spot_result["steps"]["scene_inventory"] = "ok" if inventory_ok else "failed"

        # Step 2: Export (optional)
        if args.export:
            export_ok = run_script(
                "02_export_sample_images.py", config_path, project_args
            )
            spot_result["steps"]["export"] = "ok" if export_ok else "failed"
        else:
            spot_result["steps"]["export"] = "skipped"

        # Step 3: Conditions lookup (reads dates from scene inventory manifest)
        if inventory_ok:
            manifest_path = default_manifest_path("scene_inventory", slug)
            conditions_ok = run_script(
                "03_check_conditions.py",
                config_path,
                ["--dates-file", str(manifest_path),
                 "--limit", str(args.conditions_limit)],
            )
            spot_result["steps"]["conditions"] = "ok" if conditions_ok else "failed"
        else:
            spot_result["steps"]["conditions"] = "skipped (no inventory)"

        results.append(spot_result)

    # Write combined manifest with processing run metadata
    run_id = generate_run_id()
    output_path = args.output or Path("pipeline/data/manifests/feasibility_run.json")

    run_manifest = build_run_manifest(
        run_id=run_id,
        region="nova-scotia",
        spots=[load_region_config(c)["slug"] for c in configs],
    )
    run_manifest["script"] = "04_run_feasibility.py"
    run_manifest["spot_results"] = results

    write_json(output_path, run_manifest)

    # Summary
    print(f"\n\n{'='*60}")
    print("Feasibility Run Summary")
    print(f"{'='*60}")
    for r in results:
        steps = r["steps"]
        status = "OK" if all(v in ("ok", "skipped") for v in steps.values()) else "ISSUES"
        print(f"  {r['slug']:<25} {status}  ({steps})")
    print(f"\nManifest: {output_path}")


if __name__ == "__main__":
    main()
