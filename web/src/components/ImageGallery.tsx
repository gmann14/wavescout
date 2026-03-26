"use client";

import { useState, useCallback, useEffect } from "react";
import Image from "next/image";
import type { GalleryScene } from "@/types";

interface Props {
  scenes: GalleryScene[];
}

export default function ImageGallery({ scenes }: Props) {
  const [nirMode, setNirMode] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

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
      ? lightboxScene.nir_path
      : lightboxScene.rgb_path
    : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-slate-300">
          Satellite Gallery
        </h4>
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
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
        {scenes.map((scene, i) => {
          const path = nirMode ? scene.nir_path : scene.rgb_path;
          if (!path) return null;
          return (
            <div
              key={`${scene.date}-${nirMode}`}
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
              <div className="p-2 text-xs">
                <div className="text-slate-300">{scene.date}</div>
                <div className="flex justify-between text-slate-500">
                  <span>{scene.swell_height_m.toFixed(1)}m swell</span>
                  <span>{Math.round(scene.foam_fraction * 100)}% foam</span>
                </div>
                {scene.tide_state && scene.tide_state !== 'unknown' && (
                  <div className="text-slate-500 mt-0.5">
                    🌊 {scene.tide_state} tide{scene.tide_m != null ? ` (${scene.tide_m.toFixed(1)}m)` : ''}
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
                <span className="text-teal-400">{lightboxScene.swell_height_m.toFixed(1)}m swell</span>
                <span className="text-slate-400 mx-3">|</span>
                <span className="text-orange-400">{Math.round(lightboxScene.foam_fraction * 100)}% foam</span>
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
