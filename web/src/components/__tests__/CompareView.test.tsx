import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CompareView from "../CompareView";
import { loadGallery } from "@/lib/data";
import type { GalleryManifest } from "@/types";

let currentDateParam: string | null = null;

vi.mock("next/navigation", () => ({
  useSearchParams: () => ({
    get: (key: string) => (key === "date" ? currentDateParam : null),
  }),
}));

vi.mock("next/image", () => ({
  default: ({
    fill: _fill,
    priority: _priority,
    unoptimized: _unoptimized,
    ...props
  }: React.ImgHTMLAttributes<HTMLImageElement> & {
    fill?: boolean;
    priority?: boolean;
    unoptimized?: boolean;
  }) => <img {...props} alt={props.alt ?? ""} />,
}));

vi.mock("@/lib/data", () => ({
  loadGallery: vi.fn(),
}));

const baseGallery: GalleryManifest = {
  run_id: "run-123",
  generated_at_utc: "2026-04-18T00:00:00Z",
  code_version: "abc123",
  parameters: {},
  summary: {
    total_spots: 3,
    total_images: 3,
  },
  spots: [
    {
      spot_name: "Lawrencetown Beach",
      slug: "lawrencetown-beach",
      publication_status: "public_named",
      scenes: [
        {
          date: "2026-01-15",
          scene_id: "lawrencetown-beach:2026-01-15",
          swell_height_m: 1.4,
          swell_period_s: 10,
          swell_direction_deg: 145,
          cloud_pct: 0,
          foam_fraction: 0.32,
          quality_score: 100,
          quality_status: "usable",
          bin_label: "moderate",
          rgb_path: "/gallery/lawrencetown-beach/example.png",
          nir_path: "/gallery/lawrencetown-beach/example-nir.png",
        },
      ],
    },
    {
      spot_name: "Cow Bay",
      slug: "cow-bay",
      publication_status: "public_named",
      scenes: [
        {
          date: "2026-01-15",
          scene_id: "cow-bay:2026-01-15",
          swell_height_m: 1.5,
          swell_period_s: 11,
          swell_direction_deg: 150,
          cloud_pct: 0,
          foam_fraction: 0.18,
          quality_score: 100,
          quality_status: "usable",
          bin_label: "moderate",
          rgb_path: "/gallery/cow-bay/example.png",
          nir_path: "/gallery/cow-bay/example-nir.png",
        },
      ],
    },
    {
      spot_name: "Martinique Beach",
      slug: "martinique-beach",
      publication_status: "public_named",
      scenes: [
        {
          date: "2026-01-15",
          scene_id: "martinique-beach:2026-01-15",
          swell_height_m: 1.6,
          swell_period_s: 10,
          swell_direction_deg: 152,
          cloud_pct: 0,
          foam_fraction: 0.1,
          quality_score: 100,
          quality_status: "usable",
          bin_label: "moderate",
          rgb_path: "/gallery/martinique-beach/example.png",
          nir_path: "/gallery/martinique-beach/example-nir.png",
        },
      ],
    },
  ],
};

describe("CompareView", () => {
  beforeEach(() => {
    currentDateParam = null;
    vi.mocked(loadGallery).mockReset();
  });

  it("shows the default same-date explanation", async () => {
    vi.mocked(loadGallery).mockResolvedValue(baseGallery);

    render(<CompareView />);

    await waitFor(() => {
      expect(screen.getByText(/Every comparison card groups scenes from the same acquisition date only./i)).toBeInTheDocument();
    });
  });

  it("shows the exact compare error state copy", async () => {
    vi.mocked(loadGallery).mockRejectedValue(new Error("boom"));

    render(<CompareView />);

    await waitFor(() => {
      expect(screen.getByText("Comparison data failed to load.")).toBeInTheDocument();
    });
  });

  it("shows the sparse direct-date banner for low-coverage dates", async () => {
    currentDateParam = "2026-02-01";
    vi.mocked(loadGallery).mockResolvedValue({
      ...baseGallery,
      spots: [
        {
          ...baseGallery.spots[0],
          scenes: [
            {
              ...baseGallery.spots[0].scenes[0],
              date: "2026-02-01",
              scene_id: "lawrencetown-beach:2026-02-01",
            },
          ],
        },
        {
          ...baseGallery.spots[1],
          scenes: [],
        },
        {
          ...baseGallery.spots[2],
          scenes: [],
        },
      ],
      summary: {
        total_spots: 1,
        total_images: 1,
      },
    });

    render(<CompareView />);

    await waitFor(() => {
      expect(screen.getByText("Sparse comparison")).toBeInTheDocument();
    });
    expect(
      screen.getByText("This date has limited coverage and is shown because it was requested directly.")
    ).toBeInTheDocument();
  });

  it("shows a no-match state for missing direct dates", async () => {
    currentDateParam = "2026-03-20";
    vi.mocked(loadGallery).mockResolvedValue(baseGallery);

    render(<CompareView />);

    await waitFor(() => {
      expect(screen.getByText("No comparison scenes were found for this date.")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "Return to all comparisons" })).toHaveAttribute("href", "/compare");
  });

  it("promotes a featured scene with acquisition readout for each date", async () => {
    vi.mocked(loadGallery).mockResolvedValue(baseGallery);

    render(<CompareView />);

    const featured = await screen.findAllByTestId("compare-featured-scene");
    expect(featured.length).toBeGreaterThan(0);

    const readouts = screen.getAllByTestId("compare-featured-readout");
    expect(readouts[0]).toHaveTextContent(/2026/);
    expect(readouts[0]).toHaveTextContent(/m/i);
    expect(readouts[0]).toHaveTextContent(/spot/i);
  });

  it("does not show NIR, foam, or %foam anywhere in the default compare view", async () => {
    vi.mocked(loadGallery).mockResolvedValue(baseGallery);

    render(<CompareView />);

    await screen.findAllByTestId("compare-featured-scene");

    const filterBar = screen.queryByTestId("compare-filters");
    if (filterBar) {
      expect(filterBar).not.toHaveTextContent(/NIR/i);
      expect(filterBar).not.toHaveTextContent(/RGB/i);
    }

    const readouts = screen.getAllByTestId("compare-featured-readout");
    for (const readout of readouts) {
      expect(readout).not.toHaveTextContent(/foam/i);
      expect(readout).not.toHaveTextContent(/NIR/i);
      expect(readout).not.toHaveTextContent(/%/);
    }

    expect(screen.queryByText(/%\s*foam/i)).toBeNull();

    const detectionDetails = screen.getByTestId("compare-detection-details");
    expect(detectionDetails).toHaveAttribute("data-open", "false");
  });
});
