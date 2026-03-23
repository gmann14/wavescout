"""
Step 1.4: For a list of Sentinel-2 image dates, query Open-Meteo
for ocean and weather conditions at that time. Build a conditions table.

Queries both Open-Meteo Marine API (waves, swell) and Open-Meteo Weather API
(wind speed, wind direction) and joins them per observation.

Run examples:
    python3 pipeline/scripts/03_check_conditions.py 2024-09-15 2024-08-20
    python3 pipeline/scripts/03_check_conditions.py --dates-file step1_output.txt
    python3 pipeline/scripts/03_check_conditions.py --lat 44.6375 --lon -63.3417 2024-09-15

Reads image dates from Step 1.1 output or accepts dates as arguments.
"""

import argparse
from datetime import datetime, timezone
import re
from pathlib import Path

from _script_utils import (
    DEFAULT_CONFIG_PATH,
    default_manifest_path,
    load_region_config,
    write_json,
)

DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def get_marine_conditions(lat: float, lon: float, date: str) -> dict | None:
    """Query Open-Meteo Marine API for conditions on a specific date.

    Args:
        lat: Latitude
        lon: Longitude
        date: Date string in YYYY-MM-DD format

    Returns:
        Dict with hourly conditions for that date, or None on error.
    """
    import requests

    url = "https://marine-api.open-meteo.com/v1/marine"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date,
        "end_date": date,
        "hourly": ",".join([
            "wave_height",
            "wave_direction",
            "wave_period",
            "swell_wave_height",
            "swell_wave_direction",
            "swell_wave_period",
            "wind_wave_height",
        ]),
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"  Error fetching marine conditions for {date}: {e}")
        return None


def get_weather_conditions(lat: float, lon: float, date: str) -> dict | None:
    """Query Open-Meteo Weather API for wind conditions on a specific date.

    Uses the archive endpoint for historical dates and the forecast endpoint
    for recent/future dates.

    Args:
        lat: Latitude
        lon: Longitude
        date: Date string in YYYY-MM-DD format

    Returns:
        Dict with hourly weather for that date, or None on error.
    """
    import requests
    from datetime import date as date_type, timedelta

    parsed = date_type.fromisoformat(date)
    # Archive API covers dates older than ~5 days; forecast covers recent dates
    if parsed < date_type.today() - timedelta(days=5):
        url = "https://archive-api.open-meteo.com/v1/archive"
    else:
        url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date,
        "end_date": date,
        "hourly": ",".join([
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
        ]),
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"  Error fetching weather conditions for {date}: {e}")
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Query Open-Meteo Marine API for Sentinel-2 observation dates. "
            "Provide dates as positional arguments or extract them from a text file."
        )
    )
    parser.add_argument(
        "dates",
        nargs="*",
        help="Observation dates in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--dates-file",
        type=Path,
        help=(
            "Path to a text file containing dates. The file may be a plain list of "
            "dates or saved output from 01_test_gee_access.py."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to region config JSON. Default: {DEFAULT_CONFIG_PATH}",
    )
    parser.add_argument(
        "--lat",
        type=float,
        help="Override latitude from the region config.",
    )
    parser.add_argument(
        "--lon",
        type=float,
        help="Override longitude from the region config.",
    )
    parser.add_argument(
        "--location-name",
        help="Override the location label from the region config.",
    )
    parser.add_argument(
        "--hour",
        type=int,
        default=11,
        help="UTC hour to summarize from the hourly response. Default: 11",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Max number of dates to query conditions for. Default: all.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Optional manifest output path. Defaults to "
            "pipeline/data/manifests/<slug>_conditions_manifest.json"
        ),
    )
    return parser.parse_args()


def validate_date(date: str) -> str:
    if not DATE_PATTERN.fullmatch(date):
        raise ValueError(f"Invalid date format: {date!r}. Expected YYYY-MM-DD.")
    return date


def extract_dates_from_file(path: Path) -> list[str]:
    text = path.read_text()
    matches = DATE_PATTERN.findall(text)

    # Preserve order while deduplicating.
    seen = set()
    dates = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            dates.append(match)
    return dates


def load_dates(args: argparse.Namespace) -> list[str]:
    dates = []

    if args.dates_file is not None:
        if not args.dates_file.exists():
            raise FileNotFoundError(f"Dates file not found: {args.dates_file}")
        dates.extend(extract_dates_from_file(args.dates_file))

    for date in args.dates:
        validated = validate_date(date)
        if validated not in dates:
            dates.append(validated)

    if not dates:
        raise ValueError(
            "No dates provided. Pass dates as arguments or use --dates-file with "
            "a saved output file from 01_test_gee_access.py."
        )

    if args.limit is not None:
        dates = dates[:args.limit]

    return dates


def summarize_marine(data: dict, hour: int = 11) -> dict:
    """Extract marine conditions at a specific hour (default 11 UTC ~ Sentinel-2 overpass).

    Sentinel-2 overpass for NS is roughly 10:30-11:30 UTC.
    """
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return {
            "time": None,
            "wave_height_m": None,
            "wave_direction_deg": None,
            "wave_period_s": None,
            "swell_height_m": None,
            "swell_direction_deg": None,
            "swell_period_s": None,
        }

    idx = min(hour, len(times) - 1)

    return {
        "time": times[idx],
        "wave_height_m": hourly.get("wave_height", [None])[idx],
        "wave_direction_deg": hourly.get("wave_direction", [None])[idx],
        "wave_period_s": hourly.get("wave_period", [None])[idx],
        "swell_height_m": hourly.get("swell_wave_height", [None])[idx],
        "swell_direction_deg": hourly.get("swell_wave_direction", [None])[idx],
        "swell_period_s": hourly.get("swell_wave_period", [None])[idx],
    }


def summarize_weather(data: dict, hour: int = 11) -> dict:
    """Extract weather conditions at a specific hour."""
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return {
            "wind_speed_kmh": None,
            "wind_direction_deg": None,
            "wind_gusts_kmh": None,
        }

    idx = min(hour, len(times) - 1)

    return {
        "wind_speed_kmh": hourly.get("wind_speed_10m", [None])[idx],
        "wind_direction_deg": hourly.get("wind_direction_10m", [None])[idx],
        "wind_gusts_kmh": hourly.get("wind_gusts_10m", [None])[idx],
    }


def fmt(val, width=9):
    """Format a value for tabular display."""
    if val is None:
        return f"{'N/A':<{width}}"
    return f"{val:<{width}}"


def main():
    args = parse_args()
    config = load_region_config(args.config)
    point = config.get("point", {})
    lat = args.lat if args.lat is not None else point.get("lat")
    lon = args.lon if args.lon is not None else point.get("lon")
    location_name = args.location_name or config["name"]

    if lat is None or lon is None:
        raise ValueError(
            "A query point is required. Provide point.lat and point.lon in the region "
            "config or override them with --lat and --lon."
        )

    dates = load_dates(args)
    output_path = args.output or default_manifest_path(
        "conditions_manifest", config["slug"]
    )

    print(f"Querying Open-Meteo Marine + Weather APIs for {len(dates)} dates")
    print(f"Location: {lat}, {lon} ({location_name})")
    print(f"Time: ~{args.hour:02d}:00 UTC (Sentinel-2 overpass window)\n")
    print(
        f"{'Date':<12} {'Wave(m)':<9} {'Dir(°)':<8} {'Per(s)':<8} "
        f"{'Swell(m)':<10} {'SwDir':<8} {'SwPer':<8} "
        f"{'Wind(km/h)':<11} {'WDir(°)':<8} {'Gust':<8}"
    )
    print("-" * 100)

    observations = []
    for date in dates:
        marine_data = get_marine_conditions(lat, lon, date)
        weather_data = get_weather_conditions(lat, lon, date)

        marine = summarize_marine(marine_data, hour=args.hour) if marine_data else summarize_marine({})
        weather = summarize_weather(weather_data, hour=args.hour) if weather_data else summarize_weather({})

        observations.append(
            {
                "date": date,
                "location_name": location_name,
                "latitude": lat,
                "longitude": lon,
                "marine": marine,
                "weather": weather,
            }
        )

        print(
            f"{date:<12} "
            f"{fmt(marine['wave_height_m'])} "
            f"{fmt(marine['wave_direction_deg'], 8)} "
            f"{fmt(marine['wave_period_s'], 8)} "
            f"{fmt(marine['swell_height_m'], 10)} "
            f"{fmt(marine['swell_direction_deg'], 8)} "
            f"{fmt(marine['swell_period_s'], 8)} "
            f"{fmt(weather['wind_speed_kmh'], 11)} "
            f"{fmt(weather['wind_direction_deg'], 8)} "
            f"{fmt(weather['wind_gusts_kmh'], 8)}"
        )

    payload = {
        "script": "03_check_conditions.py",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": config["_config_path"],
        "region": {
            "name": location_name,
            "slug": config["slug"],
            "region": config.get("region"),
            "point": {"lat": lat, "lon": lon},
            "bbox": config.get("bbox"),
        },
        "query": {
            "summary_hour_utc": args.hour,
            "dates": dates,
            "data_sources": {
                "marine": "Open-Meteo Marine API (marine-api.open-meteo.com)",
                "weather": "Open-Meteo Weather API (api.open-meteo.com)",
            },
        },
        "observations": observations,
    }
    write_json(output_path, payload)
    print(f"\nResults saved to {output_path}")
    print("\nNext: compare these conditions with your reviewed imagery observations.")


if __name__ == "__main__":
    main()
