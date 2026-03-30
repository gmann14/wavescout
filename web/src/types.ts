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
  // Composite ranking fields (from 20_rank_segments.py)
  composite_score?: number;
  confidence?: number;
  foam_component?: number;
  profile_component?: number;
  geometry_component?: number;
  foam_obs_count?: number;
  turn_on_threshold?: number;
  optimal_swell?: string;
  primary_direction?: string;
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
  swell_period_s?: number;
  swell_direction_deg?: number;
  cloud_pct?: number;
  foam_fraction: number;
  quality_score?: number;
  wave_energy?: number;
  bin_label: string;
  rgb_path: string | null;
  nir_path: string | null;
  annotated_rgb_path?: string | null;
  annotated_nir_path?: string | null;
  tide_m?: number | null;
  tide_state?: string | null;
}

export interface GallerySpot {
  spot_name: string;
  slug: string;
  scenes: GalleryScene[];
}

export interface GalleryManifest {
  spots: GallerySpot[];
}

// --- Atlas types ---

import type { Polygon } from "geojson";

export interface AtlasSectionProperties {
  section_id: string;
  centroid_lat: number;
  centroid_lon: number;
  mean_score: number;
  max_score: number;
  segment_count: number;
  segment_ids: string[];
  coastline_length_m: number;
}

export type AtlasSectionsGeoJSON = FeatureCollection<
  Polygon,
  AtlasSectionProperties
>;

export interface AtlasGallerySection {
  section_id: string;
  section_name: string;
  slug: string;
  mean_score: number;
  max_score: number;
  segment_count: number;
  segment_ids: string[];
  coastline_length_m: number;
  scenes: GalleryScene[];
}

export interface AtlasGalleryManifest {
  sections: AtlasGallerySection[];
}

// --- Break flag types ---

export type BreakType = 'point' | 'beach' | 'reef' | 'unknown';
export type ConfidenceLevel = 'certain' | 'likely' | 'maybe';

export interface BreakFlag {
  id: string;
  section_id: string;
  lat: number;
  lon: number;
  note: string;
  break_type: BreakType;
  confidence: ConfidenceLevel;
  flagged_at: string;
}
