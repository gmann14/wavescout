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
      console.error("Missing NEXT_PUBLIC_MAPBOX_TOKEN");
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
      const [spots, segHigh, segAll, galleryData] = await Promise.all([
        loadSpots(),
        loadSegmentsHigh(),
        loadSegmentsAll(),
        loadGallery(),
      ]);

      if (abortController.signal.aborted) return;
      setGallery(galleryData);

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
            20, "#475569",  // dim gray — minimal evidence
            40, "#eab308",  // yellow — moderate potential
            60, "#fb923c",  // orange — strong candidate
            80, "#14b8a6",  // bright teal — confirmed break
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
            ["get", "confidence"],
            "high", "#14b8a6",
            "medium", "#2dd4bf",
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
        // Parse JSON-encoded properties from mapbox
        const spotProps: SpotProperties = {
          name: props.name,
          slug: props.slug,
          type: props.type,
          swell_window: props.swell_window,
          notes: props.notes,
          confidence: props.confidence,
          source: props.source,
          foam_summary: props.foam_summary
            ? JSON.parse(props.foam_summary)
            : null,
          has_swell_profile: props.has_swell_profile === true || props.has_swell_profile === "true",
        };
        handleSpotClick(spotProps);
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
        const confidence = typeof props.confidence === "number" ? props.confidence : undefined;
        const foamComponent = typeof props.foam_component === "number" ? props.foam_component : undefined;
        const profileComponent = typeof props.profile_component === "number" ? props.profile_component : undefined;

        let detailHtml = "";
        if (foamComponent != null && foamComponent > 0) {
          detailHtml += `<div>Foam: ${foamComponent.toFixed(1)}/40</div>`;
        }
        if (profileComponent != null && profileComponent > 0) {
          detailHtml += `<div>Profile: ${profileComponent.toFixed(1)}/25</div>`;
        }
        if (props.primary_direction) {
          detailHtml += `<div>Dir: ${props.primary_direction}</div>`;
        }

        segPopup
          .setLngLat(geom.coordinates as [number, number])
          .setHTML(
            `<div class="text-xs">
              <div class="font-medium" style="color:${getScoreColor(displayScore)}">${props.id}</div>
              <div>Score: ${displayScore}/100</div>
              <div>${getConfidenceBadge(confidence)}</div>
              ${props.rank ? `<div>Rank: #${props.rank}</div>` : ""}
              ${detailHtml}
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

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-navy-900/90 backdrop-blur border border-navy-700 rounded-lg p-3 text-xs space-y-1.5 z-10 hidden sm:block">
        <div className="text-slate-400 font-medium mb-1">Legend</div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-teal-500 border-2 border-white inline-block" />
          <span className="text-slate-300">Verified spots (20)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-orange-400 inline-block" />
          <span className="text-slate-300">High-scoring candidates</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-600 inline-block" />
          <span className="text-slate-300">Scored segments</span>
        </div>
      </div>

      {/* Stats bar */}
      <div className="absolute top-4 left-4 bg-navy-900/90 backdrop-blur border border-navy-700 rounded-lg px-3 py-2 text-xs z-10">
        <span className="text-teal-400 font-bold">16,939</span>
        <span className="text-slate-500"> segments scored</span>
        <span className="text-slate-600 mx-1.5">|</span>
        <span className="text-orange-400 font-bold">2,420</span>
        <span className="text-slate-500"> high candidates</span>
        <span className="text-slate-600 mx-1.5">|</span>
        <span className="text-white font-bold">20</span>
        <span className="text-slate-500"> verified</span>
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
