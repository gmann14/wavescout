"use client";

import { useEffect, useState } from "react";
import type { SpotProperties, SpotDetail, GalleryScene } from "@/types";
import { loadSpotDetail } from "@/lib/data";
import SwellChart from "./SwellChart";
import ImageGallery from "./ImageGallery";

interface Props {
  spot: SpotProperties;
  gallery: GalleryScene[];
  onClose: () => void;
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full border ${color}`}
    >
      {label}
    </span>
  );
}

function ScoreBar({
  label,
  value,
  max,
}: {
  label: string;
  value: number;
  max: number;
}) {
  const pct = Math.round((value / max) * 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-24 text-slate-400 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-navy-800 rounded-full overflow-hidden">
        <div
          className="h-full bg-teal-500 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-8 text-right text-slate-500 tabular-nums">
        {value}
      </span>
    </div>
  );
}

export default function SpotPanel({ spot, gallery, onClose }: Props) {
  const [detail, setDetail] = useState<SpotDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    loadSpotDetail(spot.slug)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [spot.slug]);

  const isConfirmed =
    spot.confidence === "high" || spot.confidence === "medium";

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-30 lg:hidden"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed bottom-0 left-0 right-0 lg:top-12 lg:right-auto lg:left-auto lg:w-96 z-40 max-h-[80vh] lg:max-h-[calc(100vh-3rem)] lg:h-auto overflow-y-auto bg-[#0f1629] border-t lg:border-t-0 lg:border-l border-[#1e2d4d] rounded-t-2xl lg:rounded-none">
        {/* Header */}
        <div className="sticky top-0 bg-navy-900/95 backdrop-blur border-b border-navy-700 px-4 py-3 flex items-start justify-between z-10">
          <div>
            <h2 className="text-lg font-semibold text-white">{spot.name}</h2>
            <div className="flex gap-1.5 mt-1">
              <Badge
                label={spot.type}
                color="border-navy-600 text-slate-400"
              />
              {isConfirmed ? (
                <Badge
                  label="Confirmed"
                  color="border-teal-500/40 text-teal-400"
                />
              ) : (
                <Badge
                  label="Candidate"
                  color="border-orange-500/40 text-orange-400"
                />
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 p-1"
            aria-label="Close panel"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path
                d="M15 5L5 15M5 5l10 10"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        <div className="p-4 space-y-5">
          {/* Spot info */}
          <div className="text-sm text-slate-400">
            <p>{spot.notes}</p>
            <p className="mt-1">
              <span className="text-slate-500">Swell window:</span>{" "}
              {spot.swell_window}
            </p>
            <p>
              <span className="text-slate-500">Source:</span> {spot.source}
            </p>
          </div>

          {/* Detection stats */}
          {spot.foam_summary && (
            <div className="bg-navy-800 rounded-lg p-3 grid grid-cols-2 gap-3 text-center">
              <div>
                <div className="text-xl font-bold text-teal-400 tabular-nums">
                  {spot.foam_summary.total_detections.toLocaleString()}
                </div>
                <div className="text-xs text-slate-500">observations</div>
              </div>
              <div>
                <div className="text-xl font-bold text-slate-200 tabular-nums">
                  {spot.foam_summary.scenes_processed}
                </div>
                <div className="text-xs text-slate-500">satellite passes</div>
              </div>
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="text-center py-4 text-slate-500 text-sm">
              Loading spot data...
            </div>
          )}

          {/* Swell profile */}
          {detail?.swell_profile && (
            <div>
              <h3 className="text-sm font-medium text-slate-300 mb-2">
                Swell Response Profile
              </h3>
              <SwellChart profile={detail.swell_profile} />

              {/* Profile metrics */}
              <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                {detail.swell_profile.turn_on_threshold_m != null && (
                  <div className="bg-navy-800 rounded-lg p-2">
                    <div className="text-sm font-bold text-orange-400 tabular-nums">
                      {detail.swell_profile.turn_on_threshold_m.toFixed(1)}m
                    </div>
                    <div className="text-[10px] text-slate-500">Turn-on</div>
                  </div>
                )}
                {detail.swell_profile.optimal_range && (
                  <div className="bg-navy-800 rounded-lg p-2">
                    <div className="text-sm font-bold text-teal-400 tabular-nums">
                      {detail.swell_profile.optimal_range.best_bin}
                    </div>
                    <div className="text-[10px] text-slate-500">Optimal</div>
                  </div>
                )}
                {detail.swell_profile.blow_out_point_m != null && (
                  <div className="bg-navy-800 rounded-lg p-2">
                    <div className="text-sm font-bold text-red-400 tabular-nums">
                      {detail.swell_profile.blow_out_point_m.toFixed(1)}m
                    </div>
                    <div className="text-[10px] text-slate-500">Blow-out</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Satellite gallery */}
          {gallery.length > 0 && <ImageGallery scenes={gallery} />}

          {/* Score breakdown - for confirmed spots with foam data */}
          {detail?.swell_profile && (
            <div>
              <h3 className="text-sm font-medium text-slate-300 mb-2">
                Profile Stats
              </h3>
              <div className="space-y-1.5">
                <ScoreBar
                  label="Segments"
                  value={detail.swell_profile.segment_count}
                  max={30}
                />
                <ScoreBar
                  label="Observations"
                  value={detail.swell_profile.total_observations}
                  max={2000}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
