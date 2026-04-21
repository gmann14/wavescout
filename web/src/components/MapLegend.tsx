interface Props {
  spotCount: number;
  highCandidateCount: number;
  segmentCount: number;
}

function LegendRow({
  marker,
  title,
}: {
  marker: React.ReactNode;
  title: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="shrink-0" aria-hidden="true">
        {marker}
      </span>
      <div className="text-slate-300">{title}</div>
    </div>
  );
}

export default function MapLegend({
  spotCount,
  highCandidateCount,
  segmentCount,
}: Props) {
  return (
    <div className="absolute bottom-4 left-4 z-10 hidden rounded-lg border border-navy-700 bg-navy-900/90 p-3 text-xs backdrop-blur sm:block">
      <div className="mb-2 text-slate-400 font-medium">Legend</div>
      <div className="flex flex-wrap gap-x-4 gap-y-2">
        <LegendRow
          marker={<span className="inline-block h-3 w-3 rounded-full border-2 border-white bg-teal-500" />}
          title={`Named spots (${spotCount || "..."})`}
        />
        <LegendRow
          marker={<span className="inline-block h-2.5 w-2.5 rounded-full bg-orange-400" />}
          title={`Candidate segments (${highCandidateCount || "..."})`}
        />
        <LegendRow
          marker={<span className="inline-block h-1.5 w-1.5 rounded-full bg-slate-500" />}
          title={`Context coastline (${segmentCount || "..."})`}
        />
      </div>
    </div>
  );
}
