import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ImageGallery from "../ImageGallery";
import type { GalleryScene } from "@/types";

vi.mock("next/image", () => ({
  default: ({
    fill: _fill,
    unoptimized: _unoptimized,
    ...props
  }: React.ImgHTMLAttributes<HTMLImageElement> & {
    fill?: boolean;
    unoptimized?: boolean;
  }) => (
    <img {...props} alt={props.alt ?? ""} />
  ),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...props
  }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const scenes: GalleryScene[] = [
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
    rgb_path: "/gallery/example.png",
    nir_path: "/gallery/example-nir.png",
    annotated_rgb_path: "/gallery/example-annotated.png",
    annotated_nir_path: "/gallery/example-nir-annotated.png",
  },
];

describe("ImageGallery", () => {
  it("opens the lightbox from a keyboard-triggered thumbnail", async () => {
    const user = userEvent.setup();
    render(<ImageGallery scenes={scenes} />);

    const trigger = screen.getByRole("button", {
      name: "Open gallery image for 2026-01-15",
    });

    trigger.focus();
    await user.keyboard("{Enter}");

    expect(
      screen.getByRole("dialog", {
        name: "Satellite gallery image for 2026-01-15",
      })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Close gallery lightbox" })
    ).toBeInTheDocument();
  });
});
