"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { SpotProperties, SpotDetail, GalleryScene } from "@/types";
import { loadSpotDetail } from "@/lib/data";
import {
  formatBreakType,
  formatEvidenceLabel,
  formatVerificationStatus,
} from "@/lib/spotData";
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
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);
  const headingId = useId();

  useEffect(() => {
    setLoading(true);
    loadSpotDetail(spot.slug)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [spot.slug]);

  useEffect(() => {
    previousActiveElementRef.current = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    closeButtonRef.current?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      previousActiveElementRef.current?.focus();
    };
  }, [onClose]);

  const activeDetail = detail ?? null;
  const summary =
    activeDetail?.explanation.summary ||
    spot.explanation.summary ||
    spot.short_summary;
  const highlights = activeDetail?.explanation.highlights ?? spot.explanation.highlights;
  const caveats = activeDetail?.explanation.caveats ?? spot.explanation.caveats;
  const surfPotentialScore = activeDetail?.surf_potential_score ?? spot.surf_potential_score;
  const evidenceLabel =
    activeDetail?.evidence_confidence_label ?? spot.evidence_confidence_label;
  const verificationStatus =
    activeDetail?.verification_status ?? spot.verification_status;
  const foamSummary = activeDetail?.foam_summary ?? spot.foam_summary;
  const gallerySceneCount = activeDetail?.gallery_summary.scene_count ?? gallery.length;
  const usableSceneCount = activeDetail?.gallery_summary.usable_scene_count ?? gallery.length;

  return (
    <>
      {/* Mobile backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-30 lg:hidden"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        className="fixed bottom-0 left-0 right-0 lg:top-12 lg:right-auto lg:left-auto lg:w-96 z-40 max-h-[80vh] lg:max-h-[calc(100vh-3rem)] lg:h-auto overflow-y-auto bg-[#0f1629] border-t lg:border-t-0 lg:border-l border-[#1e2d4d] rounded-t-2xl lg:rounded-none"
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
      >
        {/* Header */}
        <div className="sticky top-0 bg-navy-900/95 backdrop-blur border-b border-navy-700 px-4 py-3 flex items-start justify-between z-10">
          <div>
            <h2 id={headingId} className="text-lg font-semibold text-white">{spot.name}</h2>
            <div className="flex gap-1.5 mt-1">
              <Badge
                label={formatBreakType(spot.break_type)}
                color="border-navy-600 text-slate-400"
              />
              <Badge
                label={formatVerificationStatus(verificationStatus)}
                color={
                  verificationStatus === "confirmed"
                    ? "border-teal-500/40 text-teal-400"
                    : "border-orange-500/40 text-orange-400"
                }
              />
              <Badge
                label={formatEvidenceLabel(evidenceLabel)}
                color={
                  evidenceLabel === "high"
                    ? "border-teal-500/40 text-teal-300"
                    : evidenceLabel === "moderate"
                      ? "border-cyan-500/40 text-cyan-300"
                      : "border-orange-500/40 text-orange-300"
                }
              />
            </div>
          </div>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className="rounded p-1 text-slate-500 hover:text-slate-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 focus-visible:ring-offset-2 focus-visible:ring-offset-[#0f1629]"
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
          <div className="text-sm text-bone-dim">
            <p className="leading-relaxed">{summary}</p>

            {/* Peer hero: score + confidence at equal visual tier */}
            <div className="mt-4 grid grid-cols-2 gap-2">
              <div
                data-testid="spot-score"
                className="tier-hero bg-navy-800 rounded-lg p-3 border border-navy-700"
              >
                <div className="text-[10px] font-readout uppercase tracking-[0.12em] text-bone-mute">
                  Surf potential
                </div>
                <div
                  data-testid="spot-score-value"
                  className="hero-number font-display text-3xl font-semibold text-bone tabular-nums mt-0.5 leading-none"
                >
                  {surfPotentialScore.toFixed(1)}
                </div>
                <div className="text-[10px] text-bone-mute mt-1 font-readout">
                  out of 100
                </div>
              </div>
              <div
                data-testid="spot-confidence"
                className="tier-hero bg-navy-800 rounded-lg p-3 border border-navy-700"
              >
                <div className="text-[10px] font-readout uppercase tracking-[0.12em] text-bone-mute">
                  Evidence confidence
                </div>
                <div
                  data-testid="spot-confidence-value"
                  className="hero-number font-display text-3xl font-semibold tabular-nums mt-0.5 leading-none text-teal-300"
                >
                  {formatEvidenceLabel(evidenceLabel)}
                </div>
                <div className="text-[10px] text-bone-mute mt-1 font-readout">
                  {verificationStatus === "confirmed"
                    ? "confirmed reference"
                    : "candidate"}
                </div>
              </div>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2">
              <div className="bg-navy-800/60 rounded-lg p-2">
                <div className="text-[10px] font-readout uppercase tracking-[0.12em] text-bone-mute">
                  Gallery scenes
                </div>
                <div className="text-base font-semibold text-bone tabular-nums">
                  {gallerySceneCount}
                </div>
              </div>
              <div className="bg-navy-800/60 rounded-lg p-2">
                <div className="text-[10px] font-readout uppercase tracking-[0.12em] text-bone-mute">
                  Swell window
                </div>
                <div className="text-xs text-bone">
                  {spot.swell_window_summary || "Not yet modeled"}
                </div>
              </div>
            </div>

            <p className="mt-3 text-xs">
              <span className="text-bone-mute font-readout uppercase tracking-wider">
                Source
              </span>{" "}
              <span className="text-bone-dim">{spot.source_summary}</span>
            </p>
          </div>

          {/* Detection stats — foam demoted to exploratory telemetry */}
          {foamSummary && (
            <div className="bg-navy-800 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="text-[10px] font-readout uppercase tracking-[0.12em] text-bone-mute">
                  Exploratory detection telemetry
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-center">
                <div>
                  <div className="text-lg font-semibold text-bone tabular-nums font-readout">
                    {foamSummary.scenes_with_foam?.toLocaleString() ??
                      foamSummary.total_detections.toLocaleString()}
                  </div>
                  <div className="text-[11px] text-bone-mute">
                    Scenes with detections
                  </div>
                </div>
                <div>
                  <div className="text-lg font-semibold text-bone tabular-nums font-readout">
                    {foamSummary.scenes_processed.toLocaleString()}
                  </div>
                  <div className="text-[11px] text-bone-mute">
                    Satellite passes analyzed
                  </div>
                </div>
              </div>
              <p className="mt-2 text-[10px] text-bone-mute leading-snug">
                Detections are exploratory. A high count suggests recurring
                activity, not confirmed surf.
              </p>
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="text-center py-4 text-slate-500 text-sm">
              Loading spot data...
            </div>
          )}

          {!loading && !detail && (
            <div className="bg-navy-800 rounded-lg p-3 text-sm text-slate-400">
              Detailed metrics are not available for this location yet.
            </div>
          )}

          {(highlights.length > 0 || caveats.length > 0) && (
            <div className="grid gap-3 md:grid-cols-2">
              {highlights.length > 0 && (
                <div className="bg-navy-800 rounded-lg p-3">
                  <h3 className="text-sm font-medium text-slate-200 mb-2">
                    Highlights
                  </h3>
                  <ul className="space-y-1 text-sm text-slate-400 list-disc list-inside">
                    {highlights.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
              {caveats.length > 0 && (
                <div className="bg-navy-800 rounded-lg p-3">
                  <h3 className="text-sm font-medium text-slate-200 mb-2">
                    Caveats
                  </h3>
                  <ul className="space-y-1 text-sm text-slate-400 list-disc list-inside">
                    {caveats.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
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

          {gallery.length === 0 && gallerySceneCount === 0 && (
            <div className="bg-navy-800 rounded-lg p-3 text-sm text-slate-400">
              No public satellite gallery scenes are available for this location yet.
            </div>
          )}

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
                  label="Detections sampled"
                  value={detail.swell_profile.total_observations}
                  max={2000}
                />
                <ScoreBar
                  label="Usable scenes"
                  value={usableSceneCount}
                  max={Math.max(gallerySceneCount, 1)}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
