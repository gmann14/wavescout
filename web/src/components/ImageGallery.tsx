"use client";

import { useState } from "react";
import Image from "next/image";
import type { GalleryScene } from "@/types";

interface Props {
  scenes: GalleryScene[];
}

export default function ImageGallery({ scenes }: Props) {
  const [nirMode, setNirMode] = useState(false);

  if (scenes.length === 0) {
    return (
      <p className="text-slate-500 text-sm italic">
        No satellite imagery available yet.
      </p>
    );
  }

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
              : "bg-navy-700 border-navy-600 text-slate-400 hover:text-slate-300"
          }`}
        >
          {nirMode ? "NIR" : "RGB"}
        </button>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
        {scenes.map((scene) => {
          const path = nirMode ? scene.nir_path : scene.rgb_path;
          if (!path) return null;
          return (
            <div
              key={`${scene.date}-${nirMode}`}
              className="flex-shrink-0 w-40 rounded-lg overflow-hidden bg-navy-800 border border-navy-700"
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
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
