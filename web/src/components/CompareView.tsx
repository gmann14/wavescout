"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import Image from "next/image";
import type { GalleryManifest, GalleryScene } from "@/types";
import { loadGallery } from "@/lib/data";

/** A scene with its parent spot info attached */
interface SpotScene {
  spotName: string;
  slug: string;
  scene: GalleryScene;
}

/** A date with all spots that have imagery */
interface ComparisonDate {
  date: string;
  dateLabel: string;
  spotScenes: SpotScene[];
  /** Representative swell from any scene on that date */
  swellHeight: number;
  swellPeriod: number | undefined;
  swellDirection: number | undefined;
}

function directionLabel(deg: number | undefined | null): string {
  if (deg == null) return "";
  const dirs = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
  ];
  return dirs[Math.round(deg / 22.5) % 16] ?? "";
}

function formatDate(dateStr: string): string {
  const [year, month, day] = dateStr.split("-");
  if (!year || !month || !day) return dateStr;
  const d = new Date(Number(year), Number(month) - 1, Number(day));
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

const SWELL_RANGES = [
  { label: "All swells", min: 0, max: Infinity },
  { label: "< 1m", min: 0, max: 1 },
  { label: "1 - 2m", min: 1, max: 2 },
  { label: "2 - 3m", min: 2, max: 3 },
  { label: "3m+", min: 3, max: Infinity },
] as const;

const SPOT_COUNTS = [
  { label: "3+ spots", min: 3 },
  { label: "5+ spots", min: 5 },
  { label: "8+ spots", min: 8 },
  { label: "10+ spots", min: 10 },
] as const;

export default function CompareView() {
  const searchParams = useSearchParams();
  const dateParam = searchParams.get("date");

  const [gallery, setGallery] = useState<GalleryManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [swellFilter, setSwellFilter] = useState(0);
  const [spotCountFilter, setSpotCountFilter] = useState(0);
  const [nirMode, setNirMode] = useState(false);
  const [lightbox, setLightbox] = useState<{
    dateIdx: number;
    sceneIdx: number;
  } | null>(null);

  useEffect(() => {
    loadGallery()
      .then(setGallery)
      .catch(() => setError("Failed to load gallery data."))
      .finally(() => setLoading(false));
  }, []);

  /** Build comparison dates from gallery data */
  const comparisonDates = useMemo<ComparisonDate[]>(() => {
    if (!gallery?.spots) return [];

    const byDate = new Map<string, SpotScene[]>();

    for (const spot of gallery.spots) {
      for (const scene of spot.scenes) {
        if (!scene.rgb_path) continue;
        const existing = byDate.get(scene.date);
        const entry: SpotScene = {
          spotName: spot.spot_name,
          slug: spot.slug,
          scene,
        };
        if (existing) {
          existing.push(entry);
        } else {
          byDate.set(scene.date, [entry]);
        }
      }
    }

    // When filtering by a specific date param, include dates with fewer spots
    const minSpotsForInclusion = dateParam ? 1 : 3;

    const dates: ComparisonDate[] = [];
    for (const [date, spotScenes] of byDate) {
      if (spotScenes.length < minSpotsForInclusion) continue;

      // Sort spot scenes alphabetically by name
      spotScenes.sort((a, b) => a.spotName.localeCompare(b.spotName));

      // Use median swell as representative
      const swells = spotScenes
        .map((s) => s.scene.swell_height_m)
        .filter((v): v is number => v != null);
      swells.sort((a, b) => a - b);
      const medianSwell = swells.length > 0 ? swells[Math.floor(swells.length / 2)] : 0;

      // Pick representative period/direction from first scene with values
      const rep = spotScenes.find(
        (s) => s.scene.swell_period_s != null
      )?.scene;

      dates.push({
        date,
        dateLabel: formatDate(date),
        spotScenes,
        swellHeight: medianSwell,
        swellPeriod: rep?.swell_period_s ?? undefined,
        swellDirection: rep?.swell_direction_deg ?? undefined,
      });
    }

    // Sort by number of spots (most first), then by date descending
    dates.sort((a, b) => {
      const countDiff = b.spotScenes.length - a.spotScenes.length;
      if (countDiff !== 0) return countDiff;
      return b.date.localeCompare(a.date);
    });

    return dates;
  }, [gallery, dateParam]);

  /** Apply filters */
  const filteredDates = useMemo(() => {
    // If a specific date is requested via URL param, show only that date
    if (dateParam) {
      return comparisonDates.filter((d) => d.date === dateParam);
    }

    const swellRange = SWELL_RANGES[swellFilter];
    const minSpots = SPOT_COUNTS[spotCountFilter]?.min ?? 3;

    return comparisonDates.filter((d) => {
      if (d.spotScenes.length < minSpots) return false;
      if (swellRange) {
        if (d.swellHeight < swellRange.min || d.swellHeight >= swellRange.max) {
          return false;
        }
      }
      return true;
    });
  }, [comparisonDates, swellFilter, spotCountFilter, dateParam]);

  /** Lightbox scene lookup */
  const lightboxData = useMemo(() => {
    if (!lightbox) return null;
    const dateEntry = filteredDates[lightbox.dateIdx];
    if (!dateEntry) return null;
    const spotScene = dateEntry.spotScenes[lightbox.sceneIdx];
    if (!spotScene) return null;
    return { dateEntry, spotScene, totalInDate: dateEntry.spotScenes.length };
  }, [lightbox, filteredDates]);

  const closeLightbox = useCallback(() => setLightbox(null), []);

  const goNextScene = useCallback(() => {
    setLightbox((prev) => {
      if (!prev) return null;
      const dateEntry = filteredDates[prev.dateIdx];
      if (!dateEntry) return prev;
      const next = (prev.sceneIdx + 1) % dateEntry.spotScenes.length;
      return { ...prev, sceneIdx: next };
    });
  }, [filteredDates]);

  const goPrevScene = useCallback(() => {
    setLightbox((prev) => {
      if (!prev) return null;
      const dateEntry = filteredDates[prev.dateIdx];
      if (!dateEntry) return prev;
      const next =
        (prev.sceneIdx - 1 + dateEntry.spotScenes.length) %
        dateEntry.spotScenes.length;
      return { ...prev, sceneIdx: next };
    });
  }, [filteredDates]);

  // Keyboard navigation for lightbox
  useEffect(() => {
    if (!lightbox) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") goNextScene();
      else if (e.key === "ArrowLeft") goPrevScene();
      else if (e.key === "Escape") closeLightbox();
      else if (e.key === "n" || e.key === "N") setNirMode((m) => !m);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [lightbox, goNextScene, goPrevScene, closeLightbox]);

  if (loading) {
    return (
      <div className="text-center py-16 text-slate-500">
        Loading comparison data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16 text-red-400">{error}</div>
    );
  }

  const lightboxPath = lightboxData
    ? nirMode
      ? lightboxData.spotScene.scene.nir_path
      : lightboxData.spotScene.scene.rgb_path
    : null;

  return (
    <div>
      {/* Date-specific banner */}
      {dateParam && (
        <div className="flex items-center gap-3 mb-6 bg-navy-800 border border-navy-700 rounded-lg px-4 py-3">
          <span className="text-sm text-slate-300">
            Showing spots for{" "}
            <span className="text-white font-medium">
              {formatDate(dateParam)}
            </span>
          </span>
          <a
            href="/compare"
            className="text-xs px-2.5 py-1 rounded-full border border-slate-600 text-slate-400 hover:text-slate-200 transition-colors"
          >
            Show all dates
          </a>
        </div>
      )}

      {/* Filters (hidden when date param is active) */}
      {!dateParam && (
        <div className="flex flex-wrap items-center gap-3 mb-6">
          {/* Swell filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Swell:</span>
            <div className="flex gap-1">
              {SWELL_RANGES.map((range, i) => (
                <button
                  key={range.label}
                  onClick={() => setSwellFilter(i)}
                  className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                    swellFilter === i
                      ? "bg-teal-500/20 border-teal-500/40 text-teal-400"
                      : "bg-navy-800 border-navy-700 text-slate-400 hover:text-slate-300"
                  }`}
                >
                  {range.label}
                </button>
              ))}
            </div>
          </div>

          {/* Spot count filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Min spots:</span>
            <div className="flex gap-1">
              {SPOT_COUNTS.map((opt, i) => (
                <button
                  key={opt.label}
                  onClick={() => setSpotCountFilter(i)}
                  className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                    spotCountFilter === i
                      ? "bg-teal-500/20 border-teal-500/40 text-teal-400"
                      : "bg-navy-800 border-navy-700 text-slate-400 hover:text-slate-300"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* NIR toggle */}
          <button
            onClick={() => setNirMode(!nirMode)}
            className={`text-xs px-2.5 py-1 rounded-full border transition-colors ml-auto ${
              nirMode
                ? "bg-teal-500/20 border-teal-500/40 text-teal-400"
                : "bg-navy-800 border-navy-700 text-slate-400 hover:text-slate-300"
            }`}
          >
            {nirMode ? "NIR" : "RGB"}
          </button>
        </div>
      )}

      {/* Summary */}
      {!dateParam && (
        <p className="text-sm text-slate-500 mb-6">
          {filteredDates.length} comparison date
          {filteredDates.length !== 1 ? "s" : ""} found
          {comparisonDates.length !== filteredDates.length &&
            ` (of ${comparisonDates.length} total)`}
        </p>
      )}

      {/* Date cards */}
      {filteredDates.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          No comparison dates match these filters. Try broadening your criteria.
        </div>
      ) : (
        <div className="space-y-8">
          {filteredDates.map((cd, dateIdx) => (
            <ComparisonDateCard
              key={cd.date}
              cd={cd}
              dateIdx={dateIdx}
              nirMode={nirMode}
              onOpenLightbox={(sceneIdx) =>
                setLightbox({ dateIdx, sceneIdx })
              }
            />
          ))}
        </div>
      )}

      {/* Lightbox */}
      {lightboxData && lightboxPath && (
        <div
          className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center"
          onClick={closeLightbox}
        >
          <button
            className="absolute top-4 right-4 text-white/70 hover:text-white text-3xl z-10"
            onClick={closeLightbox}
          >
            ✕
          </button>

          <button
            className="absolute left-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white text-4xl z-10 px-2"
            onClick={(e) => {
              e.stopPropagation();
              goPrevScene();
            }}
          >
            ‹
          </button>

          <div
            className="relative max-w-[90vw] max-h-[85vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={lightboxPath}
              alt={`${lightboxData.spotScene.spotName} - ${lightboxData.dateEntry.date}`}
              className="max-w-full max-h-[85vh] object-contain rounded-lg"
            />
            <div className="absolute bottom-0 left-0 right-0 bg-black/70 backdrop-blur-sm rounded-b-lg px-4 py-3 flex items-center justify-between">
              <div>
                <span className="text-white font-medium">
                  {lightboxData.spotScene.spotName}
                </span>
                <span className="text-slate-400 mx-3">|</span>
                <span className="text-slate-300">
                  {lightboxData.dateEntry.dateLabel}
                </span>
                <span className="text-slate-400 mx-3">|</span>
                <span className="text-teal-400">
                  {(lightboxData.spotScene.scene.swell_height_m ?? 0).toFixed(1)}m
                  {lightboxData.spotScene.scene.swell_direction_deg != null
                    ? ` ${directionLabel(lightboxData.spotScene.scene.swell_direction_deg)}`
                    : ""}
                  {lightboxData.spotScene.scene.swell_period_s
                    ? ` @ ${lightboxData.spotScene.scene.swell_period_s.toFixed(0)}s`
                    : ""}
                </span>
                {(lightboxData.spotScene.scene.foam_fraction ?? 0) > 0 && (
                  <>
                    <span className="text-slate-400 mx-3">|</span>
                    <span className="text-orange-400">
                      {((lightboxData.spotScene.scene.foam_fraction ?? 0) * 100).toFixed(1)}%
                      foam
                    </span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setNirMode(!nirMode);
                  }}
                  className={`text-xs px-3 py-1 rounded-full border ${
                    nirMode
                      ? "bg-teal-500/20 border-teal-500/40 text-teal-400"
                      : "border-slate-600 text-slate-300"
                  }`}
                >
                  {nirMode ? "NIR" : "RGB"}
                </button>
                <span className="text-slate-500 text-sm">
                  {lightbox!.sceneIdx + 1} / {lightboxData.totalInDate}
                </span>
              </div>
            </div>
          </div>

          <button
            className="absolute right-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white text-4xl z-10 px-2"
            onClick={(e) => {
              e.stopPropagation();
              goNextScene();
            }}
          >
            ›
          </button>
        </div>
      )}
    </div>
  );
}

/** Individual date comparison card */
function ComparisonDateCard({
  cd,
  dateIdx,
  nirMode,
  onOpenLightbox,
}: {
  cd: ComparisonDate;
  dateIdx: number;
  nirMode: boolean;
  onOpenLightbox: (sceneIdx: number) => void;
}) {
  return (
    <div className="bg-navy-900 border border-navy-700 rounded-xl overflow-hidden">
      {/* Date header */}
      <div className="px-4 py-3 border-b border-navy-700 flex flex-wrap items-center gap-x-4 gap-y-1">
        <h3 className="text-lg font-semibold text-white">{cd.dateLabel}</h3>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-teal-400">
            {cd.swellHeight.toFixed(1)}m
            {cd.swellDirection != null
              ? ` ${directionLabel(cd.swellDirection)}`
              : ""}
            {cd.swellPeriod ? ` @ ${cd.swellPeriod.toFixed(0)}s` : ""}
          </span>
          <span className="text-slate-500">
            {cd.spotScenes.length} spot{cd.spotScenes.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Thumbnail grid */}
      <div className="p-3 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {cd.spotScenes.map((ss, sceneIdx) => {
          const path = nirMode ? ss.scene.nir_path : ss.scene.rgb_path;
          if (!path) return null;
          const foamPct = (ss.scene.foam_fraction ?? 0) * 100;
          return (
            <div
              key={ss.slug}
              className="rounded-lg overflow-hidden bg-navy-800 border border-navy-700 cursor-pointer hover:border-teal-500/50 transition-colors"
              onClick={() => onOpenLightbox(sceneIdx)}
            >
              <div className="relative aspect-square">
                <Image
                  src={path}
                  alt={`${ss.spotName} - ${cd.date}`}
                  fill
                  className="object-cover"
                  sizes="(max-width: 640px) 50vw, (max-width: 768px) 33vw, 25vw"
                />
                {/* Foam badge */}
                {foamPct > 0 && (
                  <div className="absolute top-1.5 right-1.5 bg-black/60 backdrop-blur-sm text-orange-400 text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                    {foamPct.toFixed(1)}%
                  </div>
                )}
              </div>
              <div className="px-2 py-1.5">
                <div className="text-xs text-slate-300 font-medium truncate">
                  {ss.spotName}
                </div>
                <div className="text-[10px] text-slate-500">
                  {(ss.scene.swell_height_m ?? 0).toFixed(1)}m swell
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
