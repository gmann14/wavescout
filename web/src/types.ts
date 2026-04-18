import type { FeatureCollection, Point } from "geojson";

export type VerificationStatus = "confirmed" | "candidate" | "rejected";
export type PublicationStatus = "public_named" | "public_coarse" | "internal_only";
export type EvidenceConfidenceLabel = "none" | "low" | "moderate" | "high";
export type QualityStatus = "usable" | "degraded" | "rejected";

export interface Provenance {
  run_id: string;
  generated_at_utc: string;
  code_version: string;
  config_version: string;
}

export interface ScoreComponents {
  geometry: number;
  foam: number;
  profile: number;
}

export interface Explanation {
  summary: string;
  score_components: ScoreComponents;
  highlights: string[];
  caveats: string[];
  provenance: Provenance;
}

export interface GallerySummary {
  scene_count: number;
  usable_scene_count: number;
  degraded_scene_count: number;
  latest_scene_date: string | null;
}

export interface SpotProperties {
  name: string;
  slug: string;
  break_type: string;
  verification_status: VerificationStatus;
  publication_status: PublicationStatus;
  source_summary: string;
  short_summary: string;
  swell_window_summary: string;
  surf_potential_score: number;
  evidence_confidence_level: number;
  evidence_confidence_label: EvidenceConfidenceLabel;
  gallery_available: boolean;
  swell_profile_available: boolean;
  quality_status: QualityStatus;
  foam_summary: FoamSummary | null;
  explanation: Explanation;
  type?: string;
  swell_window?: string;
  notes?: string;
  confidence?: string;
  source?: string;
  has_swell_profile?: boolean;
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
  verification_status?: VerificationStatus;
  publication_status?: PublicationStatus;
  surf_potential_score?: number;
  evidence_confidence_level?: number;
  evidence_confidence_label?: EvidenceConfidenceLabel;
  quality_status?: QualityStatus;
  score_components?: ScoreComponents;
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
  turn_on_threshold_m?: number;
  optimal_swell?: string;
  optimal_swell_range?: string;
  primary_direction?: string;
  explanation?: Explanation;
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
  verification_status: VerificationStatus;
  publication_status: PublicationStatus;
  evidence_confidence_level: number;
  evidence_confidence_label: EvidenceConfidenceLabel;
  surf_potential_score: number;
  quality_status: QualityStatus;
  swell_profile: SwellProfile | null;
  foam_summary: FoamSummary | null;
  gallery_summary: GallerySummary;
  provenance: Provenance;
  explanation: Explanation;
}

export interface GalleryScene {
  date: string;
  scene_id: string;
  swell_height_m: number;
  swell_period_s?: number;
  swell_direction_deg?: number;
  cloud_pct?: number;
  foam_fraction: number;
  quality_score?: number;
  quality_status: QualityStatus;
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
  publication_status: PublicationStatus;
  scenes: GalleryScene[];
}

export interface GalleryManifest {
  run_id: string;
  generated_at_utc: string;
  code_version: string;
  parameters: Record<string, unknown>;
  summary: Record<string, unknown>;
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
  publication_status?: PublicationStatus;
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
  publication_status?: PublicationStatus;
  scenes: GalleryScene[];
}

export interface AtlasGalleryManifest {
  summary?: Record<string, unknown>;
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
