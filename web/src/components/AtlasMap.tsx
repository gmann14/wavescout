"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  loadAtlasSections,
  loadAtlasGallery,
  loadSpots,
} from "@/lib/data";
import type {
  AtlasSectionProperties,
  AtlasGalleryManifest,
  GalleryScene,
  BreakFlag,
} from "@/types";
import AtlasSectionPanel from "./AtlasSectionPanel";
import { useBreakFlags } from "@/hooks/useBreakFlags";

const NS_CENTER: [number, number] = [-63.0, 44.7];
const NS_ZOOM = 6.5;

function scoreColor(score: number): string {
  if (score >= 70) return "#14b8a6"; // teal-500
  if (score >= 60) return "#2dd4bf"; // teal-400
  if (score >= 50) return "#fb923c"; // orange-400
  return "#64748b"; // slate-500
}

function buildFlagGeoJSON(flags: BreakFlag[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: flags.map((f) => ({
      type: "Feature" as const,
      properties: {
        id: f.id,
        section_id: f.section_id,
        note: f.note || "",
        break_type: f.break_type,
        confidence: f.confidence,
        flagged_at: f.flagged_at,
      },
      geometry: {
        type: "Point" as const,
        coordinates: [f.lon, f.lat],
      },
    })),
  };
}

function ScoreLegend() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="absolute bottom-4 left-4 bg-[#0f1629]/90 backdrop-blur border border-[#1e2d4d] rounded-lg p-3 text-xs space-y-1.5 z-10 hidden sm:block max-w-[220px]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-slate-400 font-medium mb-1 flex items-center gap-1 w-full text-left hover:text-slate-200 transition-colors"
      >
        Section Score
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          className={`transition-transform ${expanded ? "rotate-180" : ""}`}
          fill="none"
        >
          <path d="M3 5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
      <div className="flex items-center gap-2">
        <span className="w-4 h-3 rounded-sm inline-block" style={{ background: "#14b8a6", opacity: 0.5 }} />
        <span className="text-slate-300">High (70+)</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-4 h-3 rounded-sm inline-block" style={{ background: "#2dd4bf", opacity: 0.5 }} />
        <span className="text-slate-300">Good (60-70)</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-4 h-3 rounded-sm inline-block" style={{ background: "#fb923c", opacity: 0.5 }} />
        <span className="text-slate-300">Moderate (50-60)</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-4 h-3 rounded-sm inline-block" style={{ background: "#64748b", opacity: 0.5 }} />
        <span className="text-slate-300">Low (&lt;50)</span>
      </div>
      <div className="flex items-center gap-2 mt-1 pt-1 border-t border-[#1e2d4d]">
        <span className="w-3 h-3 rounded-full bg-teal-500 border-2 border-white inline-block" />
        <span className="text-slate-300">Verified spots</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="w-3 h-3 rounded-full bg-orange-500 border-2 border-white inline-block" />
        <span className="text-slate-300">Flagged breaks</span>
      </div>

      {expanded && (
        <div className="mt-2 pt-2 border-t border-[#1e2d4d] space-y-2 text-slate-400">
          <div className="text-slate-300 font-medium">How sections are scored</div>
          <div className="space-y-1.5">
            <div>
              <div className="flex justify-between">
                <span>Swell Exposure</span>
                <span className="text-slate-500">40 pts</span>
              </div>
              <div className="text-[10px] text-slate-500">Faces Atlantic swell window (140-200 deg) with open ocean fetch</div>
            </div>
            <div>
              <div className="flex justify-between">
                <span>Coastal Geometry</span>
                <span className="text-slate-500">25 pts</span>
              </div>
              <div className="text-[10px] text-slate-500">Headlands, bays, and points that focus wave energy</div>
            </div>
            <div>
              <div className="flex justify-between">
                <span>Bathymetry</span>
                <span className="text-slate-500">20 pts</span>
              </div>
              <div className="text-[10px] text-slate-500">Underwater shelf gradient from GEBCO data</div>
            </div>
            <div>
              <div className="flex justify-between">
                <span>Road Access</span>
                <span className="text-slate-500">15 pts</span>
              </div>
              <div className="text-[10px] text-slate-500">Proximity to nearest road for practical access</div>
            </div>
          </div>
          <div className="text-[10px] text-slate-500 italic pt-1">
            Scores are geometry-based predictions, not observed wave data. Use satellite imagery to verify.
          </div>
        </div>
      )}
    </div>
  );
}

export default function AtlasMap() {
  const mapContainer = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- mapbox Map dynamically imported
  const mapRef = useRef<any>(null);
  const [mounted, setMounted] = useState(false);
  const [selectedSection, setSelectedSection] =
    useState<AtlasSectionProperties | null>(null);
  const [atlasGallery, setAtlasGallery] =
    useState<AtlasGalleryManifest | null>(null);
  const [minScore, setMinScore] = useState(40);
  const [showSpots, setShowSpots] = useState(true);
  const [sectionCount, setSectionCount] = useState(0);

  const { flags, addFlag, removeFlag } = useBreakFlags();

  // Keep a ref to flags for map source updates (avoids re-running map init effect)
  const flagsRef = useRef<BreakFlag[]>(flags);
  flagsRef.current = flags;

  useEffect(() => {
    setMounted(true);
  }, []);

  // Update flag markers whenever flags change
  useEffect(() => {
    if (!mapRef.current) return;
    try {
      const source = mapRef.current.getSource("break-flags");
      if (source && typeof source.setData === "function") {
        source.setData(buildFlagGeoJSON(flags));
      }
    } catch {
      // source may not exist yet
    }
  }, [flags]);

  // Filter sections by score on the map
  useEffect(() => {
    if (!mapRef.current) return;
    const m = mapRef.current;
    try {
      if (m.getLayer("atlas-sections-fill")) {
        m.setFilter("atlas-sections-fill", [">=", ["get", "mean_score"], minScore]);
      }
      if (m.getLayer("atlas-sections-outline")) {
        m.setFilter("atlas-sections-outline", [">=", ["get", "mean_score"], minScore]);
      }
    } catch {
      // layers may not exist yet
    }
  }, [minScore]);

  // Toggle spot visibility
  useEffect(() => {
    if (!mapRef.current) return;
    const m = mapRef.current;
    try {
      for (const layerId of ["spots-glow", "spots-dot", "spots-label"]) {
        if (m.getLayer(layerId)) {
          m.setLayoutProperty(
            layerId,
            "visibility",
            showSpots ? "visible" : "none"
          );
        }
      }
    } catch {
      // layers may not exist yet
    }
  }, [showSpots]);

  useEffect(() => {
    if (!mounted || !mapContainer.current || mapRef.current) return;

    import("mapbox-gl").then((mapboxgl) => {
      const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
      if (!token) {
        console.error("Missing NEXT_PUBLIC_MAPBOX_TOKEN");
        return;
      }
      mapboxgl.default.accessToken = token;

      const map = new mapboxgl.default.Map({
        container: mapContainer.current!,
        style: "mapbox://styles/mapbox/satellite-streets-v12",
        center: NS_CENTER,
        zoom: NS_ZOOM,
        minZoom: 5,
        maxZoom: 15,
      });

      map.addControl(new mapboxgl.default.NavigationControl(), "top-right");
      mapRef.current = map;

      map.on("load", async () => {
        let sections, spots, gallery;
        try {
          [sections, spots, gallery] = await Promise.all([
            loadAtlasSections(),
            loadSpots(),
            loadAtlasGallery(),
          ]);
        } catch {
          // Atlas data might not exist yet — show empty map
          [sections, spots, gallery] = [
            { type: "FeatureCollection" as const, features: [] },
            { type: "FeatureCollection" as const, features: [] },
            { sections: [] },
          ];
        }

        setAtlasGallery(gallery as AtlasGalleryManifest);
        setSectionCount(sections.features?.length ?? 0);

        // --- Atlas sections layer ---
        map.addSource("atlas-sections", {
          type: "geojson",
          data: sections as GeoJSON.FeatureCollection,
        });

        // Fill
        map.addLayer({
          id: "atlas-sections-fill",
          type: "fill",
          source: "atlas-sections",
          filter: [">=", ["get", "mean_score"], 40],
          paint: {
            "fill-color": [
              "interpolate",
              ["linear"],
              ["get", "mean_score"],
              30,
              "#64748b",
              50,
              "#fb923c",
              60,
              "#2dd4bf",
              70,
              "#14b8a6",
            ],
            "fill-opacity": 0.25,
          },
        });

        // Outline
        map.addLayer({
          id: "atlas-sections-outline",
          type: "line",
          source: "atlas-sections",
          filter: [">=", ["get", "mean_score"], 40],
          paint: {
            "line-color": [
              "interpolate",
              ["linear"],
              ["get", "mean_score"],
              30,
              "#64748b",
              50,
              "#fb923c",
              60,
              "#2dd4bf",
              70,
              "#14b8a6",
            ],
            "line-width": [
              "interpolate",
              ["linear"],
              ["zoom"],
              6,
              0.5,
              10,
              2,
            ],
            "line-opacity": 0.7,
          },
        });

        // --- Spot pins ---
        map.addSource("spots", {
          type: "geojson",
          data: spots as GeoJSON.FeatureCollection,
        });
        map.addLayer({
          id: "spots-glow",
          type: "circle",
          source: "spots",
          paint: {
            "circle-radius": 12,
            "circle-color": "#14b8a6",
            "circle-opacity": 0.2,
            "circle-blur": 1,
          },
        });
        map.addLayer({
          id: "spots-dot",
          type: "circle",
          source: "spots",
          paint: {
            "circle-radius": 6,
            "circle-color": "#14b8a6",
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 2,
          },
        });
        map.addLayer({
          id: "spots-label",
          type: "symbol",
          source: "spots",
          layout: {
            "text-field": ["get", "name"],
            "text-size": 11,
            "text-offset": [0, 1.5],
            "text-anchor": "top",
            "text-optional": true,
          },
          paint: {
            "text-color": "#e2e8f0",
            "text-halo-color": "#0a0e1a",
            "text-halo-width": 1.5,
          },
        });

        // --- Break flag markers ---
        map.addSource("break-flags", {
          type: "geojson",
          data: buildFlagGeoJSON(flagsRef.current),
        });
        map.addLayer({
          id: "break-flags-glow",
          type: "circle",
          source: "break-flags",
          paint: {
            "circle-radius": 10,
            "circle-color": "#f97316",
            "circle-opacity": 0.25,
            "circle-blur": 0.8,
          },
        });
        map.addLayer({
          id: "break-flags-dot",
          type: "circle",
          source: "break-flags",
          paint: {
            "circle-radius": 5,
            "circle-color": "#f97316",
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1.5,
          },
        });

        // --- Click handlers ---
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- mapbox event
        map.on("click", "atlas-sections-fill", (e: any) => {
          if (!e.features?.[0]) return;
          const props = e.features[0].properties;
          if (!props) return;
          // Parse stringified arrays
          const segmentIds =
            typeof props.segment_ids === "string"
              ? JSON.parse(props.segment_ids)
              : props.segment_ids ?? [];
          setSelectedSection({
            section_id: props.section_id,
            centroid_lat: props.centroid_lat,
            centroid_lon: props.centroid_lon,
            mean_score: props.mean_score,
            max_score: props.max_score,
            segment_count: props.segment_count,
            segment_ids: segmentIds,
            coastline_length_m: props.coastline_length_m,
          });
        });

        // Hover popup for sections
        const popup = new mapboxgl.default.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 8,
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- mapbox event
        map.on("mouseenter", "atlas-sections-fill", (e: any) => {
          map.getCanvas().style.cursor = "pointer";
          if (!e.features?.[0]) return;
          const p = e.features[0].properties;
          const geom = e.features[0].geometry;
          if (!p) return;
          const lngLat =
            geom.type === "Polygon"
              ? [p.centroid_lon, p.centroid_lat]
              : (e.lngLat as [number, number]);

          popup
            .setLngLat(lngLat as [number, number])
            .setHTML(
              `<div class="text-xs">
                <div class="font-medium" style="color:${scoreColor(p.mean_score)}">${p.section_id}</div>
                <div>Score: ${p.mean_score}/100</div>
                <div>${p.segment_count} segments</div>
              </div>`
            )
            .addTo(map);
        });

        map.on("mouseleave", "atlas-sections-fill", () => {
          map.getCanvas().style.cursor = "";
          popup.remove();
        });

        // Flag hover popup
        const flagPopup = new mapboxgl.default.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 8,
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- mapbox event
        map.on("mouseenter", "break-flags-dot", (e: any) => {
          map.getCanvas().style.cursor = "pointer";
          if (!e.features?.[0]) return;
          const p = e.features[0].properties;
          const geom = e.features[0].geometry;
          if (!p) return;

          const note = p.note ? `<div class="text-slate-300">${p.note}</div>` : "";
          flagPopup
            .setLngLat(geom.coordinates as [number, number])
            .setHTML(
              `<div class="text-xs" style="max-width:180px">
                <div class="font-medium" style="color:#f97316">${p.break_type} break</div>
                <div>Confidence: ${p.confidence}</div>
                <div>${p.section_id}</div>
                ${note}
              </div>`
            )
            .addTo(map);
        });

        map.on("mouseleave", "break-flags-dot", () => {
          map.getCanvas().style.cursor = "";
          flagPopup.remove();
        });

        // Spot hover
        map.on("mouseenter", "spots-dot", () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "spots-dot", () => {
          map.getCanvas().style.cursor = "";
        });
      });
    });

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [mounted]);

  // Gallery scenes for selected section
  const sectionGallery: GalleryScene[] =
    selectedSection && atlasGallery
      ? (
          atlasGallery.sections.find(
            (s) => s.section_id === selectedSection.section_id
          )?.scenes ?? []
        )
      : [];

  const handleExportFlags = useCallback(() => {
    // Enrich flags with section metadata from atlas gallery
    const enriched = flags.map((f) => {
      const sec = atlasGallery?.sections.find(
        (s) => s.section_id === f.section_id
      );
      return {
        ...f,
        section_name: sec?.section_name ?? null,
        section_mean_score: sec?.mean_score ?? null,
      };
    });

    const json = JSON.stringify(enriched, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `wavescout-flags-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [flags, atlasGallery]);

  if (!mounted) {
    return (
      <div className="absolute inset-0 flex items-center justify-center text-slate-500">
        Loading atlas...
      </div>
    );
  }

  return (
    <>
      <div
        ref={mapContainer}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          width: "100%",
          height: "100%",
        }}
      />

      {/* Controls panel */}
      <div className="absolute top-4 left-4 bg-[#0f1629]/90 backdrop-blur border border-[#1e2d4d] rounded-lg p-3 z-10 space-y-3">
        <div className="text-xs flex items-center gap-2">
          <div>
            <span className="text-teal-400 font-bold">{sectionCount.toLocaleString()}</span>
            <span className="text-slate-500"> atlas sections</span>
          </div>
          {flags.length > 0 && (
            <span className="bg-orange-500/20 border border-orange-500/40 text-orange-400 text-[10px] font-medium px-1.5 py-0.5 rounded-full tabular-nums">
              {flags.length} flag{flags.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Score filter */}
        <div className="space-y-1">
          <label className="text-xs text-slate-400 flex justify-between">
            <span>Min score</span>
            <span className="text-slate-300 tabular-nums">{minScore}</span>
          </label>
          <input
            type="range"
            min={20}
            max={80}
            step={5}
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-full h-1.5 rounded-full appearance-none bg-navy-800 accent-teal-500"
          />
        </div>

        {/* Spot toggle */}
        <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={showSpots}
            onChange={(e) => setShowSpots(e.target.checked)}
            className="rounded border-navy-600 bg-navy-800 text-teal-500 accent-teal-500"
          />
          Show verified spots
        </label>

        {/* Export flags */}
        {flags.length > 0 && (
          <button
            onClick={handleExportFlags}
            className="w-full text-xs bg-[#162038] hover:bg-[#1a2744] border border-[#1e2d4d] text-slate-400 hover:text-slate-300 py-1.5 rounded transition-colors flex items-center justify-center gap-1.5"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path
                d="M6 2v6M3 5l3 3 3-3M2 10h8"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Export Flags
          </button>
        )}
      </div>

      {/* Legend */}
      <ScoreLegend />

      {/* Section detail panel */}
      {selectedSection && (
        <AtlasSectionPanel
          section={selectedSection}
          gallery={sectionGallery}
          onClose={() => setSelectedSection(null)}
          onAddFlag={addFlag}
          existingFlags={flags}
          onRemoveFlag={removeFlag}
        />
      )}

      {/* Missing token warning */}
      {!process.env.NEXT_PUBLIC_MAPBOX_TOKEN && (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0a0e1a]/90 z-50">
          <div className="bg-[#162038] border border-[#1e2d4d] rounded-xl p-8 max-w-md text-center">
            <h2 className="text-xl font-bold text-white mb-2">
              Mapbox Token Required
            </h2>
            <p className="text-slate-400 text-sm">
              Set{" "}
              <code className="text-teal-400">NEXT_PUBLIC_MAPBOX_TOKEN</code> in
              your <code className="text-teal-400">.env.local</code> file.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
