import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Nav from "../Nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/compare",
}));

describe("Nav", () => {
  it("renders the primary routes", () => {
    render(<Nav />);

    expect(screen.getByRole("link", { name: /WaveScout/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Map" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Compare" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "How It Works" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "About" })).toBeInTheDocument();
  });

  it("marks the current route as active", () => {
    render(<Nav />);

    expect(screen.getByRole("link", { name: "Compare" }).className).toMatch(/text-teal-400/);
  });
});
