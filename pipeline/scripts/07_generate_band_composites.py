#!/usr/bin/env python3
"""Generate multi-band composite thumbnails from GEE for surf detection feasibility.

Produces several band combinations that may reveal foam/whitecaps better than RGB:
1. NIR highlight (B8) — water absorbs NIR, foam/whitecaps reflect it
2. SWIR-NIR-Green false color (B11, B8, B3) — highlights wet/dry/foam boundaries
3. NDWI (B3-B8)/(B3+B8) — water index, foam shows as anomalies in shallow water
4. B8-B4 difference — isolates NIR reflectance above visible baseline (foam signature)

Targets specific dates for swell vs flat comparison.
"""

import json
import os
from pathlib import Path

import ee
import requests
from dotenv import load_dotenv

# Comparison dates with known conditions
COMPARISON_DATES = {
    "2023-11-19": {"swell_m": 3.8, "label": "BIGGEST"},
    "2025-04-02": {"swell_m": 2.0, "label": "medium_swell"},
    "2023-02-22": {"swell_m": 1.6, "label": "moderate_swell"},
    "2024-08-30": {"swell_m": 0.3, "label": "FLAT"},
    "2022-05-03": {"swell_m": 0.3, "label": "FLAT"},
    "2023-08-23": {"swell_m": 0.4, "label": "FLAT"},
}

BAND_COMBOS = {
    "NIR": {
        "bands": ["B8", "B8", "B8"],
        "min": 0, "max": 2000, "gamma": 1.4,
        "desc": "NIR single-band (foam reflects, water absorbs)"
    },
    "SWIR-NIR-G": {
        "bands": ["B11", "B8", "B3"],
        "min": 0, "max": 3000, "gamma": 1.3,
        "desc": "SWIR-NIR-Green false color (wet/dry/foam boundaries)"
    },
    "NIR-R-G": {
        "bands": ["B8", "B4", "B3"],
        "min": 0, "max": 3000, "gamma": 1.3,
        "desc": "Color infrared (vegetation red, foam bright)"
    },
}


def find_scene_for_date(target_date, bbox, tolerance_days=3):
    """Find closest clear scene to target date."""
    start = ee.Date(target_date).advance(-tolerance_days, "day")
    end = ee.Date(target_date).advance(tolerance_days, "day")
    
    scenes = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(bbox)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    
    count = scenes.size().getInfo()
    if count == 0:
        return None
    return ee.Image(scenes.first())


def generate_ndwi(image, bbox, width):
    """Generate NDWI image: (Green - NIR) / (Green + NIR). Foam anomalies in water."""
    green = image.select("B3").toFloat()
    nir = image.select("B8").toFloat()
    ndwi = green.subtract(nir).divide(green.add(nir)).rename("NDWI")
    
    # Map NDWI to a diverging color palette
    # Water = high positive (blue), Land = negative (brown), Foam = near-zero anomaly
    vis_params = {
        "bands": ["NDWI"],
        "min": -0.3,
        "max": 0.8,
        "palette": ["8B4513", "D2B48C", "FFFFCC", "90EE90", "00BFFF", "0000FF"],
        "dimensions": width,
        "region": bbox,
        "format": "png",
    }
    return ndwi.getThumbURL(vis_params)


def main():
    load_dotenv()
    project = os.getenv("GEE_PROJECT", "seotakeoff")
    ee.Initialize(project=project)

    config = json.load(open("pipeline/configs/lawrencetown-beach.json"))
    bbox = ee.Geometry.Rectangle(config["bbox"])
    
    outdir = Path("pipeline/data/thumbnails/band_composites")
    outdir.mkdir(parents=True, exist_ok=True)
    
    width = 1024
    
    print("Generating band composites for Lawrencetown Beach")
    print(f"Output: {outdir}/\n")
    
    for date_str, info in COMPARISON_DATES.items():
        swell = info["swell_m"]
        label = info["label"]
        
        print(f"\n--- {date_str} ({swell}m swell, {label}) ---")
        
        image = find_scene_for_date(date_str, bbox)
        if image is None:
            print(f"  No clear scene found near {date_str}, skipping")
            continue
        
        actual_date = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd").getInfo()
        cloud = image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()
        print(f"  Using scene from {actual_date} (cloud: {cloud:.0f}%)")
        
        # Generate each band combo
        for combo_name, combo in BAND_COMBOS.items():
            vis_params = {
                "bands": combo["bands"],
                "min": combo["min"],
                "max": combo["max"],
                "gamma": combo["gamma"],
                "dimensions": width,
                "region": bbox,
                "format": "png",
            }
            
            url = image.getThumbURL(vis_params)
            fname = f"lawrencetown_{actual_date}_{swell}m_{label}_{combo_name}.png"
            print(f"  {combo_name}: {combo['desc']} ... ", end="", flush=True)
            
            resp = requests.get(url)
            if resp.status_code == 200:
                with open(outdir / fname, "wb") as f:
                    f.write(resp.content)
                print(f"OK ({len(resp.content)//1024}KB)")
            else:
                print(f"FAILED ({resp.status_code})")
        
        # NDWI
        print(f"  NDWI: water index (foam = anomaly) ... ", end="", flush=True)
        try:
            url = generate_ndwi(image, bbox, width)
            fname = f"lawrencetown_{actual_date}_{swell}m_{label}_NDWI.png"
            resp = requests.get(url)
            if resp.status_code == 200:
                with open(outdir / fname, "wb") as f:
                    f.write(resp.content)
                print(f"OK ({len(resp.content)//1024}KB)")
            else:
                print(f"FAILED ({resp.status_code})")
        except Exception as e:
            print(f"ERROR: {e}")
    
    print(f"\n✅ Done! Composites saved to {outdir}/")
    print("\nKey things to look for:")
    print("  NIR: Bright spots in water = foam/whitecaps (water should be dark)")
    print("  SWIR-NIR-G: Bright cyan/white in water = foam")
    print("  NDWI: Anomalous light patches in the blue water zone = foam")
    print("  NIR-R-G: Bright white patches in dark water = breaking waves")


if __name__ == "__main__":
    main()
