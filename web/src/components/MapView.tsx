"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import mapboxgl from "mapbox-gl";
import type {
  SpotsGeoJSON,
  SegmentsGeoJSON,
  SpotProperties,
  GalleryManifest,
  GalleryScene,
} from "@/types";
import {
  loadSpots,
  loadSegmentsHigh,
  loadSegmentsAll,
  loadGallery,
} from "@/lib/data";
import { normalizeSpotProperties } from "@/lib/spotData";
import MapLegend from "./MapLegend";
import SpotPanel from "./SpotPanel";

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
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [selectedSpot, setSelectedSpot] = useState<SpotProperties | null>(null);
  const [gallery, setGallery] = useState<GalleryManifest | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [stats, setStats] = useState({
    segmentCount: 0,
    highCandidateCount: 0,
    spotCount: 0,
  });

  const handleSpotClick = useCallback(
    (props: SpotProperties) => {
      setSelectedSpot(props);
    },
    []
  );

  // Initialize map
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
    if (!token) {
      setLoadError("Map token missing. Set NEXT_PUBLIC_MAPBOX_TOKEN to render the map.");
      return;
    }
    mapboxgl.accessToken = token;

    const m = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: NS_CENTER,
      zoom: NS_ZOOM,
      minZoom: 5,
      maxZoom: 15,
    });

    m.addControl(new mapboxgl.NavigationControl(), "top-right");

    m.on("load", () => {
      map.current = m;
      setMapReady(true);
    });

    return () => {
      m.remove();
      map.current = null;
    };
  }, []);

  // Load data and add layers once map is ready
  useEffect(() => {
    if (!mapReady || !map.current) return;
    const m = map.current;

    const abortController = new AbortController();

    async function addLayers() {
      setIsLoadingData(true);
      try {
        const [spots, segHigh, segAll, galleryData] = await Promise.all([
          loadSpots(),
          loadSegmentsHigh(),
          loadSegmentsAll(),
          loadGallery(),
        ]);

        if (abortController.signal.aborted) return;
        setGallery(galleryData);
        setStats({
          segmentCount: segAll.features.length,
          highCandidateCount: segHigh.features.length,
          spotCount: spots.features.length,
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
              5, 1,
              8, 2,
              12, 4,
            ],
            "circle-color": "#334155",
            "circle-opacity": [
              "interpolate",
              ["linear"],
              ["zoom"],
              5, 0,
              8, 0.3,
              10, 0.5,
            ],
          },
        });

        // --- Layer 2: High-scoring segments (>60) - colored dots ---
        m.addSource("segments-high", {
          type: "geojson",
          data: segHigh,
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
              5, 2,
              8, 4,
              12, 6,
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
              5, 0.4,
              8, 0.7,
              12, 0.9,
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
          "circle-radius": 16,
          "circle-color": "#14b8a6",
          "circle-opacity": 0.15,
          "circle-blur": 1,
        },
        });

      // Inner dot
        m.addLayer({
          id: "spots-dot",
        type: "circle",
        source: "spots",
        paint: {
          "circle-radius": 7,
          "circle-color": [
            "match",
            ["get", "evidence_confidence_label"],
            "high", "#14b8a6",
            "moderate", "#2dd4bf",
            "low", "#fb923c",
            "#fb923c",
          ],
          "circle-stroke-width": 2,
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
          "text-size": 12,
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

      // --- Click handlers ---
        m.on("click", "spots-dot", (e) => {
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

        m.on("mouseenter", "segments-high", (e) => {
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

  // Get gallery scenes for selected spot
  const spotGallery: GalleryScene[] =
    selectedSpot && gallery
      ? gallery.spots.find((s) => s.slug === selectedSpot.slug)?.scenes ?? []
      : [];

  return (
    <div className="relative flex-1" style={{ minHeight: 0 }}>
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
        </div>
      </div>

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
