"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import type {
  SpotProperties,
  GalleryManifest,
  GalleryScene,
  AtlasGalleryManifest,
  AtlasSectionProperties,
  BreakFlag,
} from "@/types";
import {
  loadSpots,
  loadSegmentsHigh,
  loadSegmentsAll,
  loadGallery,
  loadAtlasSections,
  loadAtlasGallery,
} from "@/lib/data";
import { normalizeSpotProperties } from "@/lib/spotData";
import MapLegend from "./MapLegend";
import SpotPanel from "./SpotPanel";
import AtlasSectionPanel from "./AtlasSectionPanel";
import { useBreakFlags } from "@/hooks/useBreakFlags";

// Nova Scotia center
const NS_CENTER: [number, number] = [-63.0, 44.7];
const NS_ZOOM = 6.5;

function getScoreColor(score: number): string {
  if (score >= 80) return "#14b8a6"; // bright teal — confirmed break
  if (score >= 60) return "#fb923c"; // orange — strong candidate
  if (score >= 40) return "#eab308"; // yellow — moderate potential
  if (score >= 20) return "#64748b"; // gray — low signal
  return "#475569"; // dim gray — minimal evidence
}

function getConfidenceBadge(confidence: number | undefined): string {
  if (confidence === 3) return '<span style="color:#22c55e">Satellite verified</span>';
  if (confidence === 2) return '<span style="color:#eab308">Partial data</span>';
  return '<span style="color:#94a3b8">Geometry only</span>';
}

export default function MapView() {
  const searchParams = useSearchParams();
  const mapContainer = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- mapbox Map dynamically imported
  const mapRef = useRef<any>(null);
  const mapboxglRef = useRef<typeof import("mapbox-gl").default | null>(null);
  const [selectedSpot, setSelectedSpot] = useState<SpotProperties | null>(null);
  const [selectedSection, setSelectedSection] =
    useState<AtlasSectionProperties | null>(null);
  const [gallery, setGallery] = useState<GalleryManifest | null>(null);
  const [atlasGallery, setAtlasGallery] = useState<AtlasGalleryManifest | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [stats, setStats] = useState({
    segmentCount: 0,
    highCandidateCount: 0,
    spotCount: 0,
    atlasSectionCount: 0,
  });
  const { flags, addFlag, removeFlag } = useBreakFlags();
  const flagsRef = useRef<BreakFlag[]>(flags);
  flagsRef.current = flags;

  const handleSpotClick = useCallback(
    (props: SpotProperties) => {
      setSelectedSection(null);
      setSelectedSpot(props);
    },
    []
  );

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    setShowAnalysis(searchParams.get("analysis") === "atlas");
  }, [mounted, searchParams]);

  useEffect(() => {
    if (!mapRef.current) return;
    try {
      const source = mapRef.current.getSource("break-flags");
      if (source && typeof source.setData === "function") {
        source.setData({
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
        });
      }
    } catch {
      // source may not exist yet
    }
  }, [flags]);

  // Initialize map
  useEffect(() => {
    if (!mounted || !mapContainer.current || mapRef.current) return;

    import("mapbox-gl").then((mapboxgl) => {
      const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
      if (!token) {
        setLoadError("Map token missing. Set NEXT_PUBLIC_MAPBOX_TOKEN to render the map.");
        return;
      }

      mapboxglRef.current = mapboxgl.default;
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

      map.on("load", () => {
        setMapReady(true);
      });
    });

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [mounted]);

  // Load data and add layers once map is ready
  useEffect(() => {
    if (!mapReady || !mapRef.current || !mapboxglRef.current) return;
    const m = mapRef.current;
    const mapboxgl = mapboxglRef.current;

    const abortController = new AbortController();

    async function addLayers() {
      setIsLoadingData(true);
      try {
        const [spots, segHigh, segAll, galleryData, atlasSections, atlasGalleryData] = await Promise.all([
          loadSpots(),
          loadSegmentsHigh(),
          loadSegmentsAll(),
          loadGallery(),
          loadAtlasSections(),
          loadAtlasGallery(),
        ]);

        const displayHighCandidates = {
          ...segHigh,
          features: segHigh.features.filter((feature) => {
            return feature.properties?.map_display_eligible === true;
          }),
        };

        if (abortController.signal.aborted) return;
        setGallery(galleryData);
        setAtlasGallery(atlasGalleryData);
        setStats({
          segmentCount: segAll.features.length,
          highCandidateCount: displayHighCandidates.features.length,
          spotCount: spots.features.length,
          atlasSectionCount: atlasSections.features.length,
        });
        setLoadError(null);

        // --- Layer 1: All scored segments (>40) - tiny dots ---
        m.addSource("segments-all", {
          type: "geojson",
          data: segAll,
        });

        m.addLayer({
          id: "segments-all",
          type: "circle",
          source: "segments-all",
          paint: {
            "circle-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              5, 1.5,
              8, 2.5,
              12, 4.5,
            ],
            "circle-color": "#93c5fd",
            "circle-opacity": [
              "interpolate",
              ["linear"],
              ["zoom"],
              5, 0,
              8, 0.18,
              10, 0.28,
            ],
          },
        });

        // --- Layer 2: High-scoring segments (>60) - colored dots ---
        m.addSource("segments-high", {
          type: "geojson",
          data: displayHighCandidates,
        });

        m.addLayer({
          id: "segments-high",
          type: "circle",
          source: "segments-high",
          paint: {
            "circle-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              5, 2.5,
              8, 4.5,
              12, 7,
            ],
            "circle-color": [
              "interpolate",
              ["linear"],
              ["get", "score"],
              20, "#475569",
              40, "#eab308",
              60, "#fb923c",
              80, "#14b8a6",
            ],
            "circle-opacity": [
              "interpolate",
              ["linear"],
              ["zoom"],
              5, 0.45,
              8, 0.75,
              12, 0.92,
            ],
            "circle-stroke-width": 1,
            "circle-stroke-color": "rgba(0,0,0,0.3)",
          },
        });

        // --- Layer 3: Verified spots - prominent pins ---
        m.addSource("spots", {
          type: "geojson",
          data: spots,
        });

      // Outer glow
        m.addLayer({
          id: "spots-glow",
          type: "circle",
          source: "spots",
          paint: {
            "circle-radius": 18,
            "circle-color": "#14b8a6",
            "circle-opacity": 0.22,
            "circle-blur": 1,
          },
        });

      // Inner dot
        m.addLayer({
          id: "spots-dot",
          type: "circle",
          source: "spots",
          paint: {
            "circle-radius": 8,
            "circle-color": "#14b8a6",
            "circle-stroke-width": 2.5,
            "circle-stroke-color": "#ffffff",
          },
        });

      // Spot labels
        m.addLayer({
          id: "spots-label",
        type: "symbol",
        source: "spots",
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["DIN Pro Medium", "Arial Unicode MS Regular"],
          "text-size": 13,
          "text-offset": [0, 1.5],
          "text-anchor": "top",
          "text-max-width": 8,
        },
        paint: {
          "text-color": "#e2e8f0",
          "text-halo-color": "#0a0e1a",
          "text-halo-width": 1.5,
        },
        });

        m.addSource("atlas-sections", {
          type: "geojson",
          data: atlasSections,
        });

        m.addLayer({
          id: "atlas-sections-fill",
          type: "fill",
          source: "atlas-sections",
          filter: [">=", ["get", "mean_score"], 40],
          layout: {
            visibility: showAnalysis ? "visible" : "none",
          },
          paint: {
            "fill-color": [
              "interpolate",
              ["linear"],
              ["get", "mean_score"],
              30, "#64748b",
              50, "#fb923c",
              60, "#2dd4bf",
              70, "#14b8a6",
            ],
            "fill-opacity": 0.18,
          },
        });

        m.addLayer({
          id: "atlas-sections-outline",
          type: "line",
          source: "atlas-sections",
          filter: [">=", ["get", "mean_score"], 40],
          layout: {
            visibility: showAnalysis ? "visible" : "none",
          },
          paint: {
            "line-color": [
              "interpolate",
              ["linear"],
              ["get", "mean_score"],
              30, "#64748b",
              50, "#fb923c",
              60, "#2dd4bf",
              70, "#14b8a6",
            ],
            "line-width": [
              "interpolate",
              ["linear"],
              ["zoom"],
              6, 0.5,
              10, 2,
            ],
            "line-opacity": 0.75,
          },
        });

        m.addSource("break-flags", {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: flagsRef.current.map((f) => ({
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
          },
        });

        m.addLayer({
          id: "break-flags-glow",
          type: "circle",
          source: "break-flags",
          layout: {
            visibility: showAnalysis ? "visible" : "none",
          },
          paint: {
            "circle-radius": 10,
            "circle-color": "#f97316",
            "circle-opacity": 0.25,
            "circle-blur": 0.8,
          },
        });

        m.addLayer({
          id: "break-flags-dot",
          type: "circle",
          source: "break-flags",
          layout: {
            visibility: showAnalysis ? "visible" : "none",
          },
          paint: {
            "circle-radius": 5,
            "circle-color": "#f97316",
            "circle-stroke-color": "#ffffff",
            "circle-stroke-width": 1.5,
          },
        });

      // --- Click handlers ---
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- mapbox event payload
        m.on("click", "spots-dot", (e: any) => {
          if (!e.features?.[0]) return;
          const props = e.features[0].properties;
          if (!props) return;
          handleSpotClick(normalizeSpotProperties(props as Record<string, unknown>));
        });

      // Popup on hover for high-scoring segments
        const segPopup = new mapboxgl.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 8,
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- mapbox event payload
        m.on("mouseenter", "segments-high", (e: any) => {
        m.getCanvas().style.cursor = "pointer";
        if (!e.features?.[0]) return;
        const props = e.features[0].properties;
        const geom = e.features[0].geometry;
        if (!props || geom.type !== "Point") return;

        const displayScore = props.composite_score ?? props.score;
        const confidence =
          typeof props.evidence_confidence_level === "number"
            ? props.evidence_confidence_level
            : typeof props.confidence === "number"
              ? props.confidence
              : undefined;

        const directionHtml = props.primary_direction
          ? `<div class="ws-popup-row"><span class="ws-popup-key">Dir</span><span class="ws-popup-val">${props.primary_direction}</span></div>`
          : "";
        const rankHtml = props.rank
          ? `<div class="ws-popup-row"><span class="ws-popup-key">Rank</span><span class="ws-popup-val">#${props.rank}</span></div>`
          : "";

        segPopup
          .setLngLat(geom.coordinates as [number, number])
          .setHTML(
            `<div class="ws-popup">
              <div class="ws-popup-title" style="color:${getScoreColor(displayScore)}">${props.id}</div>
              <div class="ws-popup-row"><span class="ws-popup-key">Score</span><span class="ws-popup-val">${displayScore}/100</span></div>
              <div class="ws-popup-row"><span class="ws-popup-key">Evidence</span><span class="ws-popup-val">${getConfidenceBadge(confidence)}</span></div>
              ${rankHtml}
              ${directionHtml}
            </div>`
          )
          .addTo(m);
        });

        m.on("mouseleave", "segments-high", () => {
          m.getCanvas().style.cursor = "";
          segPopup.remove();
        });

        const sectionPopup = new mapboxgl.Popup({
          closeButton: false,
          closeOnClick: false,
          offset: 8,
        });

        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- mapbox event payload
        m.on("click", "atlas-sections-fill", (e: any) => {
          if (!e.features?.[0]) return;
          const props = e.features[0].properties;
          if (!props) return;
          const segmentIds =
            typeof props.segment_ids === "string"
              ? JSON.parse(props.segment_ids)
              : props.segment_ids ?? [];
          setSelectedSpot(null);
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

        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- mapbox event payload
        m.on("mouseenter", "atlas-sections-fill", (e: any) => {
          if (!e.features?.[0]) return;
          m.getCanvas().style.cursor = "pointer";
          const p = e.features[0].properties;
          if (!p) return;
          sectionPopup
            .setLngLat([p.centroid_lon, p.centroid_lat])
            .setHTML(
              `<div class="text-xs">
                <div class="font-medium" style="color:${getScoreColor(p.mean_score)}">${p.section_id}</div>
                <div>Mean score: ${p.mean_score}/100</div>
                <div>${p.segment_count} segments</div>
              </div>`
            )
            .addTo(m);
        });

        m.on("mouseleave", "atlas-sections-fill", () => {
          m.getCanvas().style.cursor = "";
          sectionPopup.remove();
        });

        // Cursor for spots
        m.on("mouseenter", "spots-dot", () => {
          m.getCanvas().style.cursor = "pointer";
        });
        m.on("mouseleave", "spots-dot", () => {
          m.getCanvas().style.cursor = "";
        });
      } catch (error) {
        console.error(error);
        if (!abortController.signal.aborted) {
          setLoadError("Map data failed to load. Refresh to retry.");
          setStats({
            segmentCount: 0,
            highCandidateCount: 0,
            spotCount: 0,
            atlasSectionCount: 0,
          });
        }
      } finally {
        if (!abortController.signal.aborted) {
          setIsLoadingData(false);
        }
      }
    }

    addLayers();

    return () => {
      abortController.abort();
    };
  }, [mapReady, handleSpotClick]);

  useEffect(() => {
    if (!mapRef.current) return;
    const visibility = showAnalysis ? "visible" : "none";
    for (const layerId of [
      "atlas-sections-fill",
      "atlas-sections-outline",
      "break-flags-glow",
      "break-flags-dot",
    ]) {
      try {
        if (mapRef.current.getLayer(layerId)) {
          mapRef.current.setLayoutProperty(layerId, "visibility", visibility);
        }
      } catch {
        // layer may not be ready yet
      }
    }
  }, [showAnalysis]);

  // Get gallery scenes for selected spot
  const spotGallery: GalleryScene[] =
    selectedSpot && gallery
      ? gallery.spots.find((s) => s.slug === selectedSpot.slug)?.scenes ?? []
      : [];
  const sectionGallery: GalleryScene[] =
    selectedSection && atlasGallery
      ? atlasGallery.sections.find((s) => s.section_id === selectedSection.section_id)?.scenes ?? []
      : [];

  return (
    <div className="relative h-full w-full" style={{ minHeight: 0 }}>
      <div ref={mapContainer} className="absolute inset-0" style={{ width: "100%", height: "100%" }} />

      {isLoadingData && !loadError && (
        <div className="absolute inset-x-4 top-4 z-20 rounded-lg border border-navy-700 bg-navy-900/95 px-4 py-3 text-sm text-slate-300 backdrop-blur">
          Loading WaveScout dataset...
        </div>
      )}

      {loadError && (
        <div className="absolute inset-x-4 top-4 z-20 rounded-lg border border-red-500/30 bg-[#160f17]/95 px-4 py-3 text-sm text-red-100 backdrop-blur">
          {loadError}
        </div>
      )}

      {!loadError && !isLoadingData && stats.segmentCount === 0 && stats.spotCount === 0 && (
        <div className="absolute inset-x-4 top-4 z-20 rounded-lg border border-navy-700 bg-navy-900/95 px-4 py-3 text-sm text-slate-300 backdrop-blur">
          No map data is available for this dataset.
        </div>
      )}

      <MapLegend
        spotCount={stats.spotCount}
        highCandidateCount={stats.highCandidateCount}
        segmentCount={stats.segmentCount}
      />

      {/* Orientation + stats bar */}
      <div className="absolute top-4 left-4 z-10 max-w-[26rem] space-y-2 map-chrome-enter">
        <div className="rounded-lg border border-navy-700 bg-navy-900/90 backdrop-blur px-3.5 py-3">
          <div className="font-readout text-[10px] uppercase tracking-[0.18em] text-bone-mute mb-1">
            Nova Scotia · Coastline atlas
          </div>
          <p className="text-[13px] leading-snug text-bone">
            Browse Nova Scotia&apos;s coast by map, then inspect satellite
            evidence and confidence.
          </p>
        </div>
        <div className="rounded-lg border border-navy-700 bg-navy-900/90 backdrop-blur px-3 py-2 text-xs font-readout flex flex-wrap items-center gap-x-2">
          <span>
            <span className="text-teal-400 font-semibold tabular-nums">
              {stats.segmentCount}
            </span>
            <span className="text-bone-mute"> segments scored</span>
          </span>
          <span className="text-navy-600">|</span>
          <span>
            <span className="text-orange-400 font-semibold tabular-nums">
              {stats.highCandidateCount}
            </span>
            <span className="text-bone-mute"> high candidates</span>
          </span>
          <span className="text-navy-600">|</span>
          <span>
            <span className="text-bone font-semibold tabular-nums">
              {stats.spotCount}
            </span>
            <span className="text-bone-mute"> named spots</span>
          </span>
          {showAnalysis && (
            <>
              <span className="text-navy-600">|</span>
              <span>
                <span className="text-bone-dim font-semibold tabular-nums">
                  {stats.atlasSectionCount}
                </span>
                <span className="text-bone-mute"> section boxes</span>
              </span>
            </>
          )}
        </div>
      </div>

      <div className="absolute left-4 top-20 z-10 max-w-[320px] rounded-lg border border-navy-700 bg-navy-900/92 px-4 py-3 text-sm text-slate-300 backdrop-blur">
        <div className="font-medium text-white">Discovery map</div>
        <p className="mt-1 text-slate-400">
          Click teal spots for known breaks. Click orange dots for exploratory leads.
        </p>
        <div className="mt-3 rounded-md border border-navy-700 bg-navy-800/70 px-3 py-2">
          <label className="flex items-start gap-2 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={showAnalysis}
              onChange={(e) => setShowAnalysis(e.target.checked)}
              className="mt-0.5 rounded border-navy-600 bg-navy-800 text-teal-500 accent-teal-500"
            />
            <span>
              <span className="font-medium text-slate-200">Show section analysis</span>
              <span className="mt-0.5 block text-slate-400">
                Overlay broader coastline boxes for deeper review and manual flagging.
              </span>
            </span>
          </label>
          {showAnalysis && (
            <div className="mt-2 text-xs text-slate-400">
              Section boxes are browsing aids, not public surf leads.
            </div>
          )}
          {showAnalysis && (
            <div className="mt-2 rounded-md border border-teal-500/20 bg-teal-500/10 px-2 py-1.5 text-xs text-teal-200">
              Click a section box to inspect coastline context, review scenes, or flag a potential break.
            </div>
          )}
          {showAnalysis && flags.length > 0 && (
            <div className="mt-2 text-xs text-orange-300">
              {flags.length} manually flagged potential break{flags.length === 1 ? "" : "s"} saved in this browser.
            </div>
          )}
        </div>
      </div>

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

      {/* Spot detail panel */}
      {selectedSpot && (
        <SpotPanel
          spot={selectedSpot}
          gallery={spotGallery}
          onClose={() => setSelectedSpot(null)}
        />
      )}

      {/* Missing token warning */}
      {!process.env.NEXT_PUBLIC_MAPBOX_TOKEN && (
        <div className="absolute inset-0 flex items-center justify-center bg-navy-950/90 z-50">
          <div className="bg-navy-800 border border-navy-600 rounded-xl p-8 max-w-md text-center">
            <h2 className="text-xl font-bold text-white mb-2">
              Mapbox Token Required
            </h2>
            <p className="text-slate-400 text-sm">
              Set <code className="text-teal-400">NEXT_PUBLIC_MAPBOX_TOKEN</code>{" "}
              in your <code className="text-teal-400">.env.local</code> file.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
