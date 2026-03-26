import type { FeatureCollection, Point } from "geojson";

export interface SpotProperties {
  name: string;
  slug: string;
  type: string;
  swell_window: string;
  notes: string;
  confidence: string;
  source: string;
  foam_summary: FoamSummary | null;
  has_swell_profile: boolean;
}

export interface FoamSummary {
  scenes_processed: number;
  segments_processed: number;
  total_detections: number;
  errors: number;
  scenes_with_foam: number;
  date_range: {
    start: string;
    end: string;
  };
}

export type SpotsGeoJSON = FeatureCollection<Point, SpotProperties>;

export interface SegmentProperties {
  id: string;
  score: number;
  swell_exposure?: number;
  geometry_score?: number;
  bathymetry?: number;
  access?: number;
  orientation?: number;
  exposure_arc?: number;
  rank?: number;
}

export type SegmentsGeoJSON = FeatureCollection<Point, SegmentProperties>;

export interface SwellBin {
  [binLabel: string]: number;
}

export interface SwellProfile {
  swell_bins: SwellBin;
  direction_bins: SwellBin;
  turn_on_threshold_m: number | null;
  optimal_range: {
    min_m: number;
    max_m: number;
    best_bin: string;
    best_mean_foam_fraction: number;
  } | null;
  blow_out_point_m: number | null;
  total_observations: number;
  segment_count: number;
}

export interface SpotDetail {
  slug: string;
  name: string;
  swell_profile: SwellProfile | null;
  foam_summary: FoamSummary | null;
}

export interface GalleryScene {
  date: string;
  swell_height_m: number;
  foam_fraction: number;
  bin_label: string;
  rgb_path: string | null;
  nir_path: string | null;
}

export interface GallerySpot {
  spot_name: string;
  slug: string;
  scenes: GalleryScene[];
}

export interface GalleryManifest {
  spots: GallerySpot[];
}
