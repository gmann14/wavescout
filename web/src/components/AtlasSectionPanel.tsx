"use client";

import { useState } from "react";
import type {
  AtlasSectionProperties,
  GalleryScene,
  BreakFlag,
  BreakType,
  ConfidenceLevel,
} from "@/types";
import ImageGallery from "./ImageGallery";

interface Props {
  section: AtlasSectionProperties;
  gallery: GalleryScene[];
  onClose: () => void;
  onAddFlag: (flag: Omit<BreakFlag, "id" | "flagged_at">) => void;
  existingFlags: BreakFlag[];
  onRemoveFlag: (id: string) => void;
}

function ScoreBadge({ score }: { score: number }) {
  let color = "border-slate-600 text-slate-400";
  if (score >= 70) color = "border-teal-500/40 text-teal-400";
  else if (score >= 60) color = "border-teal-500/30 text-teal-400/70";
  else if (score >= 50) color = "border-orange-500/40 text-orange-400";

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${color}`}>
      Score {score.toFixed(0)}
    </span>
  );
}

const BREAK_TYPES: { value: BreakType; label: string }[] = [
  { value: "unknown", label: "Unknown" },
  { value: "point", label: "Point break" },
  { value: "beach", label: "Beach break" },
  { value: "reef", label: "Reef break" },
];

const CONFIDENCE_LEVELS: { value: ConfidenceLevel; label: string }[] = [
  { value: "maybe", label: "Maybe" },
  { value: "likely", label: "Likely" },
  { value: "certain", label: "Certain" },
];

function FlagForm({
  section,
  onSave,
  onCancel,
}: {
  section: AtlasSectionProperties;
  onSave: (flag: Omit<BreakFlag, "id" | "flagged_at">) => void;
  onCancel: () => void;
}) {
  const [lat, setLat] = useState(section.centroid_lat.toFixed(5));
  const [lon, setLon] = useState(section.centroid_lon.toFixed(5));
  const [note, setNote] = useState("");
  const [breakType, setBreakType] = useState<BreakType>("unknown");
  const [confidence, setConfidence] = useState<ConfidenceLevel>("maybe");

  const handleSave = () => {
    const parsedLat = parseFloat(lat);
    const parsedLon = parseFloat(lon);
    if (isNaN(parsedLat) || isNaN(parsedLon)) return;

    onSave({
      section_id: section.section_id,
      lat: parsedLat,
      lon: parsedLon,
      note: note.trim(),
      break_type: breakType,
      confidence,
    });
  };

  const inputClass =
    "w-full bg-[#0f1629] border border-[#1e2d4d] rounded px-2.5 py-1.5 text-sm text-slate-200 focus:border-teal-500/50 focus:outline-none transition-colors";
  const labelClass = "text-xs text-slate-400 mb-1 block";

  return (
    <div className="bg-[#162038] rounded-lg p-3 space-y-3 border border-orange-500/30">
      <div className="text-sm font-medium text-orange-400">
        Flag Potential Break
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className={labelClass}>Latitude</label>
          <input
            type="text"
            value={lat}
            onChange={(e) => setLat(e.target.value)}
            className={inputClass}
            inputMode="decimal"
          />
        </div>
        <div>
          <label className={labelClass}>Longitude</label>
          <input
            type="text"
            value={lon}
            onChange={(e) => setLon(e.target.value)}
            className={inputClass}
            inputMode="decimal"
          />
        </div>
      </div>

      <div>
        <label className={labelClass}>Break type</label>
        <select
          value={breakType}
          onChange={(e) => setBreakType(e.target.value as BreakType)}
          className={inputClass}
        >
          {BREAK_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className={labelClass}>Confidence</label>
        <div className="flex gap-1.5">
          {CONFIDENCE_LEVELS.map((c) => (
            <button
              key={c.value}
              onClick={() => setConfidence(c.value)}
              className={`flex-1 text-xs py-1.5 rounded border transition-colors ${
                confidence === c.value
                  ? "bg-teal-500/20 border-teal-500/40 text-teal-400"
                  : "bg-[#0f1629] border-[#1e2d4d] text-slate-400 hover:text-slate-300"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className={labelClass}>Note</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="What did you see? (optional)"
          rows={2}
          className={`${inputClass} resize-none`}
        />
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleSave}
          className="flex-1 bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/40 text-orange-400 text-sm py-1.5 rounded transition-colors"
        >
          Save Flag
        </button>
        <button
          onClick={onCancel}
          className="flex-1 bg-[#0f1629] hover:bg-[#1a2744] border border-[#1e2d4d] text-slate-400 text-sm py-1.5 rounded transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function AtlasSectionPanel({
  section,
  gallery,
  onClose,
  onAddFlag,
  existingFlags,
  onRemoveFlag,
}: Props) {
  const [showFlagForm, setShowFlagForm] = useState(false);
  const coastlineKm = (section.coastline_length_m / 1000).toFixed(1);

  const sectionFlags = existingFlags.filter(
    (f) => f.section_id === section.section_id
  );

  const handleSaveFlag = (flag: Omit<BreakFlag, "id" | "flagged_at">) => {
    onAddFlag(flag);
    setShowFlagForm(false);
  };

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
        <div className="sticky top-0 bg-[#0f1629]/95 backdrop-blur border-b border-[#1e2d4d] px-4 py-3 flex items-start justify-between z-10">
          <div>
            <h2 className="text-lg font-semibold text-white">
              {section.section_id}
            </h2>
            <div className="flex gap-1.5 mt-1">
              <ScoreBadge score={section.mean_score} />
              <span className="text-xs px-2 py-0.5 rounded-full border border-[#1e2d4d] text-slate-400">
                {coastlineKm}km
              </span>
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
          {/* Score stats */}
          <div className="bg-[#162038] rounded-lg p-3 grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-xl font-bold text-teal-400 tabular-nums">
                {section.mean_score.toFixed(0)}
              </div>
              <div className="text-[10px] text-slate-500">Mean Score</div>
            </div>
            <div>
              <div className="text-xl font-bold text-white tabular-nums">
                {section.max_score.toFixed(0)}
              </div>
              <div className="text-[10px] text-slate-500">Max Score</div>
            </div>
            <div>
              <div className="text-xl font-bold text-slate-200 tabular-nums">
                {section.segment_count}
              </div>
              <div className="text-[10px] text-slate-500">Segments</div>
            </div>
          </div>

          {/* Section details */}
          <div className="text-sm text-slate-400 space-y-1">
            <p>
              <span className="text-slate-500">Coastline:</span>{" "}
              {coastlineKm}km
            </p>
            <p>
              <span className="text-slate-500">Location:</span>{" "}
              {section.centroid_lat.toFixed(3)}N,{" "}
              {Math.abs(section.centroid_lon).toFixed(3)}W
            </p>
            <p>
              <span className="text-slate-500">Segments:</span>{" "}
              {section.segment_ids.slice(0, 3).join(", ")}
              {section.segment_ids.length > 3 && (
                <span className="text-slate-500">
                  {" "}
                  +{section.segment_ids.length - 3} more
                </span>
              )}
            </p>
          </div>

          {/* Score breakdown bar */}
          <div>
            <h3 className="text-sm font-medium text-slate-300 mb-2">
              Section Score
            </h3>
            <div className="h-2 bg-[#162038] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${section.mean_score}%`,
                  background:
                    section.mean_score >= 70
                      ? "#14b8a6"
                      : section.mean_score >= 60
                        ? "#2dd4bf"
                        : section.mean_score >= 50
                          ? "#fb923c"
                          : "#64748b",
                }}
              />
            </div>
          </div>

          {/* Flag button / form */}
          {showFlagForm ? (
            <FlagForm
              section={section}
              onSave={handleSaveFlag}
              onCancel={() => setShowFlagForm(false)}
            />
          ) : (
            <button
              onClick={() => setShowFlagForm(true)}
              className="w-full bg-orange-500/10 hover:bg-orange-500/20 border border-orange-500/30 text-orange-400 text-sm py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                className="flex-shrink-0"
              >
                <path
                  d="M3 2v12M3 2l8 3-8 3"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Flag as Potential Break
            </button>
          )}

          {/* Existing flags for this section */}
          {sectionFlags.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-slate-300">
                Flags ({sectionFlags.length})
              </h3>
              {sectionFlags.map((flag) => (
                <div
                  key={flag.id}
                  className="bg-[#162038] rounded-lg p-2.5 border border-orange-500/20 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex gap-1.5">
                      <span className="text-orange-400 capitalize">
                        {flag.break_type}
                      </span>
                      <span className="text-slate-500">|</span>
                      <span className="text-slate-400 capitalize">
                        {flag.confidence}
                      </span>
                    </div>
                    <button
                      onClick={() => onRemoveFlag(flag.id)}
                      className="text-slate-600 hover:text-red-400 transition-colors"
                      aria-label="Remove flag"
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 14 14"
                        fill="none"
                      >
                        <path
                          d="M10.5 3.5l-7 7M3.5 3.5l7 7"
                          stroke="currentColor"
                          strokeWidth="1.5"
                          strokeLinecap="round"
                        />
                      </svg>
                    </button>
                  </div>
                  {flag.note && (
                    <p className="text-slate-400">{flag.note}</p>
                  )}
                  <p className="text-slate-600">
                    {flag.lat.toFixed(4)}, {flag.lon.toFixed(4)}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Satellite gallery */}
          {gallery.length > 0 ? (
            <ImageGallery scenes={gallery} />
          ) : (
            <div className="text-sm text-slate-500 italic">
              No satellite imagery generated for this section yet. Run script 18
              to generate gallery images.
            </div>
          )}
        </div>
      </div>
    </>
  );
}
