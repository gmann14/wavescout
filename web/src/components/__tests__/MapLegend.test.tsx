import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MapLegend from "../MapLegend";

describe("MapLegend", () => {
  it("renders non-color cues for named spots, candidates, and context coastline", () => {
    render(
      <MapLegend
        spotCount={14}
        highCandidateCount={4402}
        segmentCount={14191}
      />
    );

    expect(screen.getByText("Named spots (14)")).toBeInTheDocument();
    expect(screen.getByText("Candidate segments (4402)")).toBeInTheDocument();
    expect(screen.getByText("Context coastline (14191)")).toBeInTheDocument();
  });
});
