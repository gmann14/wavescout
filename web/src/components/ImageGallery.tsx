"use client";

import { useState, useCallback, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import type { GalleryScene } from "@/types";

function directionLabel(deg: number | undefined | null): string {
  if (deg == null) return "";
  const dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  return dirs[Math.round(deg / 22.5) % 16];
}

function tideEmoji(state: string | undefined | null): string {
  if (!state) return "";
  if (state === "high") return "⬆️";
  if (state === "low") return "⬇️";
  if (state === "mid") return "↔️";
  return "";
}

interface Props {
  scenes: GalleryScene[];
}

export default function ImageGallery({ scenes }: Props) {
  const [nirMode, setNirMode] = useState(false);
  const [showBreaks, setShowBreaks] = useState(true);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  // Check if any scene has annotated images
  const hasAnnotations = scenes.some(
    (s) => s.annotated_rgb_path || s.annotated_nir_path
  );

  const openLightbox = useCallback((index: number) => {
    setLightboxIndex(index);
  }, []);

  const closeLightbox = useCallback(() => {
    setLightboxIndex(null);
  }, []);

  const goNext = useCallback(() => {
    setLightboxIndex((i) => (i !== null ? (i + 1) % scenes.length : null));
  }, [scenes.length]);

  const goPrev = useCallback(() => {
    setLightboxIndex((i) =>
      i !== null ? (i - 1 + scenes.length) % scenes.length : null
    );
  }, [scenes.length]);

  // Keyboard navigation
  useEffect(() => {
    if (lightboxIndex === null) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") goNext();
      else if (e.key === "ArrowLeft") goPrev();
      else if (e.key === "Escape") closeLightbox();
      else if (e.key === "n" || e.key === "N") setNirMode((m) => !m);
      else if (e.key === "b" || e.key === "B") setShowBreaks((b) => !b);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [lightboxIndex, goNext, goPrev, closeLightbox]);

  if (scenes.length === 0) {
    return (
      <p className="text-slate-500 text-sm italic">
        No satellite imagery available yet.
      </p>
    );
  }

  const lightboxScene = lightboxIndex !== null ? scenes[lightboxIndex] : null;
  const lightboxPath = lightboxScene
    ? nirMode
      ? (showBreaks && lightboxScene.annotated_nir_path) || lightboxScene.nir_path
      : (showBreaks && lightboxScene.annotated_rgb_path) || lightboxScene.rgb_path
    : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-slate-300">
          Satellite Gallery
        </h4>
        <div className="flex items-center gap-2">
          {hasAnnotations && (
            <button
              onClick={() => setShowBreaks(!showBreaks)}
              className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                showBreaks
                  ? "bg-orange-500/20 border-orange-500/40 text-orange-400"
                  : "bg-[#162038] border-[#1e2d4d] text-slate-400 hover:text-slate-300"
              }`}
            >
              Breaks
            </button>
          )}
          <button
            onClick={() => setNirMode(!nirMode)}
            className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
              nirMode
                ? "bg-teal-500/20 border-teal-500/40 text-teal-400"
                : "bg-[#162038] border-[#1e2d4d] text-slate-400 hover:text-slate-300"
            }`}
          >
            {nirMode ? "NIR" : "RGB"}
          </button>
        </div>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
        {scenes.map((scene, i) => {
          const cleanPath = nirMode ? scene.nir_path : scene.rgb_path;
          const annotatedPath = nirMode ? scene.annotated_nir_path : scene.annotated_rgb_path;
          const path = (showBreaks && annotatedPath) || cleanPath;
          if (!path) return null;
          return (
            <div
              key={`${scene.date}-${nirMode}-${showBreaks}`}
              className="flex-shrink-0 w-40 rounded-lg overflow-hidden bg-[#162038] border border-[#1e2d4d] cursor-pointer hover:border-teal-500/50 transition-colors"
              onClick={() => openLightbox(i)}
            >
              <div className="relative aspect-square">
                <Image
                  src={path}
                  alt={`${scene.date} - ${scene.swell_height_m}m swell`}
                  fill
                  className="object-cover"
                  sizes="160px"
                />
              </div>
              <div className="p-2 text-xs space-y-0.5">
                <div className="text-slate-300 font-medium">{scene.date}</div>
                <div className="flex justify-between text-slate-400">
                  <span>{(scene.swell_height_m ?? 0).toFixed(1)}m {scene.swell_direction_deg != null ? directionLabel(scene.swell_direction_deg) : ''}</span>
                  <span>{scene.swell_period_s ? `${scene.swell_period_s.toFixed(0)}s` : ''}</span>
                </div>
                {scene.tide_state && scene.tide_state !== 'unknown' && (
                  <div className="text-slate-500">
                    <span>{tideEmoji(scene.tide_state)} {scene.tide_state}{scene.tide_m != null ? ` ${scene.tide_m.toFixed(1)}m` : ''}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Lightbox */}
      {lightboxScene && lightboxPath && (
        <div
          className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center"
          onClick={closeLightbox}
        >
          {/* Close button */}
          <button
            className="absolute top-4 right-4 text-white/70 hover:text-white text-3xl z-10"
            onClick={closeLightbox}
          >
            ✕
          </button>

          {/* Prev */}
          <button
            className="absolute left-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white text-4xl z-10 px-2"
            onClick={(e) => {
              e.stopPropagation();
              goPrev();
            }}
          >
            ‹
          </button>

          {/* Image */}
          <div
            className="relative max-w-[90vw] max-h-[85vh]"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={lightboxPath}
              alt={`${lightboxScene.date} - ${lightboxScene.swell_height_m}m swell`}
              className="max-w-full max-h-[85vh] object-contain rounded-lg"
            />
            {/* Info bar */}
            <div className="absolute bottom-0 left-0 right-0 bg-black/70 backdrop-blur-sm rounded-b-lg px-4 py-3 flex items-center justify-between">
              <div>
                <span className="text-white font-medium">{lightboxScene.date}</span>
                <span className="text-slate-400 mx-3">|</span>
                <span className="text-teal-400">
                  {(lightboxScene.swell_height_m ?? 0).toFixed(1)}m
                  {lightboxScene.swell_direction_deg != null ? ` ${directionLabel(lightboxScene.swell_direction_deg)}` : ''}
                  {lightboxScene.swell_period_s ? ` @ ${lightboxScene.swell_period_s.toFixed(0)}s` : ''}
                </span>
                {lightboxScene.tide_state && lightboxScene.tide_state !== 'unknown' && (
                  <>
                    <span className="text-slate-400 mx-3">|</span>
                    <span className="text-blue-400">
                      {lightboxScene.tide_state} tide{lightboxScene.tide_m != null ? ` (${lightboxScene.tide_m.toFixed(1)}m)` : ''}
                    </span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-3">
                <Link
                  href={`/compare?date=${lightboxScene.date}`}
                  className="text-xs px-3 py-1 rounded-full border border-orange-500/40 text-orange-400 hover:bg-orange-500/10 transition-colors"
                  onClick={(e) => e.stopPropagation()}
                >
                  Compare date
                </Link>
                {hasAnnotations && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowBreaks(!showBreaks);
                    }}
                    className={`text-xs px-3 py-1 rounded-full border ${
                      showBreaks
                        ? "bg-orange-500/20 border-orange-500/40 text-orange-400"
                        : "border-slate-600 text-slate-300"
                    }`}
                  >
                    Breaks
                  </button>
                )}
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
                  {lightboxIndex! + 1} / {scenes.length}
                </span>
              </div>
            </div>
          </div>

          {/* Next */}
          <button
            className="absolute right-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white text-4xl z-10 px-2"
            onClick={(e) => {
              e.stopPropagation();
              goNext();
            }}
          >
            ›
          </button>
        </div>
      )}
    </div>
  );
}
