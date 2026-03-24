from __future__ import annotations

import json
import os
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "configs" / "lawrencetown-beach.json"
)


def today_iso() -> str:
    return date.today().isoformat()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_run_id() -> str:
    """Short unique ID for a processing run."""
    return uuid4().hex[:12]


def get_code_version() -> str | None:
    """Return the current git commit hash, or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def get_gee_project() -> str | None:
    """Return the GEE project ID from the GEE_PROJECT env var, or None."""
    return os.environ.get("GEE_PROJECT")


def init_gee(project: str | None = None) -> None:
    """Initialize Google Earth Engine with a project ID.

    Resolution order: explicit argument > GEE_PROJECT env var > earthengine default.
    """
    import ee

    project = project or get_gee_project()
    if project:
        ee.Initialize(project=project)
    else:
        ee.Initialize()


def load_region_config(config_path: Path | str | None = None) -> dict:
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    with path.open() as f:
        config = json.load(f)
    config["_config_path"] = str(path)
    return config


def default_manifest_path(prefix: str, slug: str) -> Path:
    return Path("pipeline/data/manifests") / f"{slug}_{prefix}.json"


def write_json(path: Path | str, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def build_run_manifest(
    run_id: str,
    region: str,
    spots: list[str],
    data_sources: list[str] | None = None,
) -> dict:
    """Build a processing run manifest matching the spec's run_manifest.json contract.

    Fields:
        - processing_run_id
        - region
        - data_sources
        - code_version (git commit)
        - generated_at_utc
    """
    return {
        "processing_run_id": run_id,
        "region": region,
        "spots": spots,
        "data_sources": data_sources or [
            "Sentinel-2 via Google Earth Engine",
            "Open-Meteo Marine API",
            "Open-Meteo Weather API",
        ],
        "code_version": get_code_version(),
        "generated_at_utc": now_utc_iso(),
    }
