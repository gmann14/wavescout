"use client";

import { useEffect, useRef, useState } from "react";
import { loadSpots, loadGallery } from "@/lib/data";
import type { SpotProperties, GalleryManifest, GalleryScene } from "@/types";
import SpotPanel from "./SpotPanel";

const NS_CENTER: [number, number] = [-63.0, 44.7];
const NS_ZOOM = 6.5;

function getScoreColor(score: number): string {
  if (score >= 80) return "#14b8a6";
  if (score >= 70) return "#2dd4bf";
  if (score >= 60) return "#fb923c";
  return "#64748b";
}

export default function MapWrapper() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<any>(null);
  const [selectedSpot, setSelectedSpot] = useState<SpotProperties | null>(null);
  const [gallery, setGallery] = useState<GalleryManifest | null>(null);
  const [mounted, setMounted] = useState(false);

  // Only render on client
  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || !mapContainer.current || mapRef.current) return;

    // Dynamic import mapbox-gl to avoid SSR
    import("mapbox-gl").then((mapboxgl) => {
      const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
      if (!token) {
        console.error("Missing NEXT_PUBLIC_MAPBOX_TOKEN");
        return;
      }
      mapboxgl.default.accessToken = token;

      const map = new mapboxgl.default.Map({
        container: mapContainer.current!,
        style: "mapbox://styles/mapbox/dark-v11",
        center: NS_CENTER,
        zoom: NS_ZOOM,
        minZoom: 5,
        maxZoom: 15,
      });

      map.addControl(new mapboxgl.default.NavigationControl(), "top-right");
      mapRef.current = map;

      map.on("load", async () => {
        // Load spots data
        const [spots, galleryData] = await Promise.all([
          loadSpots(),
          loadGallery(),
        ]);
        setGallery(galleryData);

        // Add verified spots layer
        map.addSource("spots", { type: "geojson", data: spots });
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

        // Click handler for spots
        map.on("click", "spots-dot", (e: any) => {
          if (!e.features?.[0]) return;
          const props = e.features[0].properties;
          if (!props) return;
          setSelectedSpot({
            name: props.name,
            slug: props.slug,
            score: props.score,
            type: props.type,
            lat: props.lat,
            lng: props.lng,
          } as SpotProperties);
        });

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

  const spotGallery: GalleryScene[] = [];
  if (selectedSpot && gallery) {
    // gallery.spots is an array, find by slug
    const spots = Array.isArray(gallery.spots) ? gallery.spots : Object.values(gallery.spots || {});
    const spotEntry = spots.find((s: any) => s.slug === selectedSpot.slug);
    if (spotEntry?.scenes) {
      spotGallery.push(...spotEntry.scenes);
    }
  }

  if (!mounted) {
    return (
      <div className="absolute inset-0 flex items-center justify-center text-slate-500">
        Loading map…
      </div>
    );
  }

  return (
    <>
      <div ref={mapContainer} style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, width: "100%", height: "100%" }} />

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-[#0f1629]/90 backdrop-blur border border-[#1e2d4d] rounded-lg p-3 text-xs space-y-1.5 z-10 hidden sm:block">
        <div className="text-slate-400 font-medium mb-1">Legend</div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-teal-500 border-2 border-white inline-block" />
          <span className="text-slate-300">Verified spots (20)</span>
        </div>
      </div>

      {/* Stats bar */}
      <div className="absolute top-4 left-4 bg-[#0f1629]/90 backdrop-blur border border-[#1e2d4d] rounded-lg px-3 py-2 text-xs z-10">
        <span className="text-white font-bold">20</span>
        <span className="text-slate-500"> verified spots</span>
        <span className="text-slate-600 mx-1.5">|</span>
        <span className="text-teal-400 font-bold">16,939</span>
        <span className="text-slate-500"> segments scored</span>
      </div>

      {/* Spot detail panel */}
      {selectedSpot && (
        <SpotPanel
          spot={selectedSpot}
          gallery={spotGallery}
          onClose={() => setSelectedSpot(null)}
        />
      )}
    </>
  );
}
