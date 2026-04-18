import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import SpotPanel from "../SpotPanel";
import type { GalleryScene, SpotProperties, SpotDetail } from "@/types";
import { loadSpotDetail } from "@/lib/data";

vi.mock("@/lib/data", () => ({
  loadSpotDetail: vi.fn(),
}));

vi.mock("../SwellChart", () => ({
  default: () => <div data-testid="swell-chart">Swell chart</div>,
}));

vi.mock("../ImageGallery", () => ({
  default: () => <div data-testid="image-gallery">Image gallery</div>,
}));

const mockSpot: SpotProperties = {
  name: "Lawrencetown Beach",
  slug: "lawrencetown-beach",
  break_type: "beach",
  verification_status: "confirmed",
  publication_status: "public_named",
  source_summary: "well-known",
  short_summary: "Known reference point.",
  swell_window_summary: "S/SE",
  surf_potential_score: 96.7,
  evidence_confidence_level: 3,
  evidence_confidence_label: "high",
  gallery_available: true,
  swell_profile_available: true,
  quality_status: "usable",
  foam_summary: {
    scenes_processed: 120,
    segments_processed: 6,
    total_detections: 707,
    errors: 0,
    scenes_with_foam: 116,
    date_range: {
      start: "2021-10-07",
      end: "2026-03-18",
    },
  },
  explanation: {
    summary: "Known reference point.",
    score_components: {
      geometry: 0,
      foam: 67.7,
      profile: 29.0,
    },
    highlights: ["Reference location in the Nova Scotia dataset"],
    caveats: ["Score is a reference-entry proxy."],
    provenance: {
      run_id: "run-123",
      generated_at_utc: "2026-04-18T00:00:00Z",
      code_version: "abc123",
      config_version: "unknown",
    },
  },
  type: "beach",
  swell_window: "S/SE",
  notes: "Known reference point.",
  confidence: "high",
  source: "well-known",
  has_swell_profile: true,
};

const mockGallery: GalleryScene[] = [];

const mockDetail: SpotDetail = {
  slug: "lawrencetown-beach",
  name: "Lawrencetown Beach",
  verification_status: "confirmed",
  publication_status: "public_named",
  evidence_confidence_level: 3,
  evidence_confidence_label: "high",
  surf_potential_score: 96.7,
  quality_status: "usable",
  foam_summary: mockSpot.foam_summary,
  swell_profile: {
    swell_bins: { "1.0-1.5m": 0.2 },
    direction_bins: { SE: 0.3 },
    turn_on_threshold_m: 0.5,
    optimal_range: {
      min_m: 1.0,
      max_m: 1.5,
      best_bin: "1.0-1.5m",
      best_mean_foam_fraction: 0.3,
    },
    blow_out_point_m: 2.5,
    total_observations: 45,
    segment_count: 3,
  },
  gallery_summary: {
    scene_count: 4,
    usable_scene_count: 3,
    degraded_scene_count: 1,
    latest_scene_date: "2026-03-18",
  },
  provenance: {
    run_id: "run-123",
    generated_at_utc: "2026-04-18T00:00:00Z",
    code_version: "abc123",
    config_version: "unknown",
  },
  explanation: mockSpot.explanation,
};

describe("SpotPanel", () => {
  beforeEach(() => {
    vi.mocked(loadSpotDetail).mockReset();
  });

  it("renders a loading state before detail data resolves", () => {
    vi.mocked(loadSpotDetail).mockImplementation(
      () => new Promise(() => undefined)
    );

    render(<SpotPanel spot={mockSpot} gallery={mockGallery} onClose={() => undefined} />);

    expect(screen.getByText("Loading spot data...")).toBeInTheDocument();
  });

  it("renders the swell profile once detail data loads", async () => {
    vi.mocked(loadSpotDetail).mockResolvedValue(mockDetail);

    render(<SpotPanel spot={mockSpot} gallery={mockGallery} onClose={() => undefined} />);

    await waitFor(() => {
      expect(screen.getByTestId("swell-chart")).toBeInTheDocument();
    });

    expect(screen.getByText("Swell Response Profile")).toBeInTheDocument();
    expect(screen.getAllByText("High evidence")).toHaveLength(2);
    expect(screen.getByText("Known reference point.")).toBeInTheDocument();
  });

  it("renders a missing-data fallback when detail loading fails", async () => {
    vi.mocked(loadSpotDetail).mockRejectedValue(new Error("boom"));

    render(<SpotPanel spot={mockSpot} gallery={mockGallery} onClose={() => undefined} />);

    await waitFor(() => {
      expect(screen.getByText("Detailed metrics are not available for this location yet.")).toBeInTheDocument();
    });
  });

  it("closes when Escape is pressed", async () => {
    vi.mocked(loadSpotDetail).mockResolvedValue(mockDetail);
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(<SpotPanel spot={mockSpot} gallery={mockGallery} onClose={onClose} />);

    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
