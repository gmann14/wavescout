import type {
  EvidenceConfidenceLabel,
  Explanation,
  FoamSummary,
  PublicationStatus,
  QualityStatus,
  SpotProperties,
  VerificationStatus,
} from "@/types";

type RawSpotValue = Record<string, unknown>;

const UNKNOWN_PROVENANCE = {
  run_id: "unknown",
  generated_at_utc: "unknown",
  code_version: "unknown",
  config_version: "unknown",
};

function parseObject<T>(value: unknown): T | null {
  if (!value) {
    return null;
  }
  if (typeof value === "string") {
    try {
      return JSON.parse(value) as T;
    } catch {
      return null;
    }
  }
  if (typeof value === "object") {
    return value as T;
  }
  return null;
}

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return fallback;
}

function toBoolean(value: unknown, fallback = false): boolean {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "string") {
    if (value === "true") {
      return true;
    }
    if (value === "false") {
      return false;
    }
  }
  return fallback;
}

function deriveEvidenceConfidenceLevel(value: unknown): number {
  if (typeof value === "number") {
    return Math.max(0, Math.min(3, Math.round(value)));
  }
  if (typeof value !== "string") {
    return 0;
  }

  const normalized = value.trim().toLowerCase();
  if (normalized === "high") {
    return 3;
  }
  if (normalized === "medium") {
    return 2;
  }
  if (normalized === "low" || normalized === "low-medium" || normalized === "medium-low") {
    return 1;
  }
  return 0;
}

function evidenceLabelForLevel(level: number): EvidenceConfidenceLabel {
  if (level >= 3) {
    return "high";
  }
  if (level === 2) {
    return "moderate";
  }
  if (level === 1) {
    return "low";
  }
  return "none";
}

function verificationStatusForRaw(
  value: unknown,
  evidenceConfidenceLevel: number,
  publicationStatus: PublicationStatus
): VerificationStatus {
  if (value === "confirmed" || value === "candidate" || value === "rejected") {
    return value;
  }
  if (publicationStatus === "public_named") {
    return "confirmed";
  }
  return evidenceConfidenceLevel >= 2 ? "confirmed" : "candidate";
}

function publicationStatusForRaw(value: unknown): PublicationStatus {
  if (value === "public_named" || value === "public_coarse" || value === "internal_only") {
    return value;
  }
  return "public_named";
}

function qualityStatusForRaw(value: unknown): QualityStatus {
  if (value === "usable" || value === "degraded" || value === "rejected") {
    return value;
  }
  return "degraded";
}

function buildFallbackExplanation(summary: string, surfPotentialScore: number): Explanation {
  return {
    summary: summary || "Known reference location included for calibration and browsing.",
    score_components: {
      geometry: 0,
      foam: Math.round(surfPotentialScore * 0.7 * 10) / 10,
      profile: Math.round(surfPotentialScore * 0.3 * 10) / 10,
    },
    highlights: [],
    caveats: [],
    provenance: UNKNOWN_PROVENANCE,
  };
}

export function normalizeSpotProperties(raw: RawSpotValue): SpotProperties {
  const foamSummary = parseObject<FoamSummary>(raw.foam_summary);
  const sourceSummary = typeof raw.source_summary === "string"
    ? raw.source_summary
    : typeof raw.source === "string"
      ? raw.source
      : "unknown";
  const shortSummary = typeof raw.short_summary === "string"
    ? raw.short_summary
    : typeof raw.notes === "string"
      ? raw.notes
      : "";
  const swellWindowSummary = typeof raw.swell_window_summary === "string"
    ? raw.swell_window_summary
    : typeof raw.swell_window === "string"
      ? raw.swell_window
      : "";

  const derivedSurfPotential = foamSummary?.scenes_processed
    ? (foamSummary.scenes_with_foam / foamSummary.scenes_processed) * 100
    : 0;
  const surfPotentialScore = toNumber(raw.surf_potential_score, derivedSurfPotential);
  const evidenceConfidenceLevel = toNumber(
    raw.evidence_confidence_level,
    deriveEvidenceConfidenceLevel(raw.confidence)
  );
  const evidenceConfidenceLabel = (
    typeof raw.evidence_confidence_label === "string"
      ? raw.evidence_confidence_label
      : evidenceLabelForLevel(evidenceConfidenceLevel)
  ) as EvidenceConfidenceLabel;
  const publicationStatus = publicationStatusForRaw(raw.publication_status);

  const explanation = parseObject<Explanation>(raw.explanation) ??
    buildFallbackExplanation(shortSummary, surfPotentialScore);

  return {
    name: String(raw.name ?? ""),
    slug: String(raw.slug ?? ""),
    break_type: typeof raw.break_type === "string"
      ? raw.break_type
      : typeof raw.type === "string"
        ? raw.type
        : "unknown",
    verification_status: verificationStatusForRaw(raw.verification_status, evidenceConfidenceLevel, publicationStatus),
    publication_status: publicationStatus,
    source_summary: sourceSummary,
    short_summary: shortSummary,
    swell_window_summary: swellWindowSummary,
    surf_potential_score: Math.round(surfPotentialScore * 10) / 10,
    evidence_confidence_level: evidenceConfidenceLevel,
    evidence_confidence_label: evidenceConfidenceLabel,
    gallery_available: toBoolean(raw.gallery_available),
    swell_profile_available: toBoolean(
      raw.swell_profile_available,
      toBoolean(raw.has_swell_profile)
    ),
    quality_status: qualityStatusForRaw(raw.quality_status),
    foam_summary: foamSummary,
    explanation,
    type: typeof raw.type === "string" ? raw.type : undefined,
    swell_window: typeof raw.swell_window === "string" ? raw.swell_window : undefined,
    notes: typeof raw.notes === "string" ? raw.notes : undefined,
    confidence: typeof raw.confidence === "string" ? raw.confidence : undefined,
    source: typeof raw.source === "string" ? raw.source : undefined,
    has_swell_profile: toBoolean(raw.has_swell_profile, false),
  };
}

export function formatBreakType(value: string): string {
  return value
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatVerificationStatus(value: VerificationStatus): string {
  if (value === "confirmed") {
    return "Confirmed";
  }
  if (value === "candidate") {
    return "Candidate";
  }
  return "Rejected";
}

export function formatEvidenceLabel(value: EvidenceConfidenceLabel): string {
  if (value === "high") {
    return "High evidence";
  }
  if (value === "moderate") {
    return "Moderate evidence";
  }
  if (value === "low") {
    return "Low evidence";
  }
  return "No evidence";
}
