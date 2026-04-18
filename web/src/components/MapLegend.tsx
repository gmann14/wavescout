interface Props {
  spotCount: number;
  highCandidateCount: number;
  segmentCount: number;
}

function LegendRow({
  marker,
  title,
  detail,
}: {
  marker: React.ReactNode;
  title: string;
  detail: string;
}) {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-0.5 shrink-0" aria-hidden="true">
        {marker}
      </span>
      <div>
        <div className="text-slate-200">{title}</div>
        <div className="text-slate-500">{detail}</div>
      </div>
    </div>
  );
}

export default function MapLegend({
  spotCount,
  highCandidateCount,
  segmentCount,
}: Props) {
  return (
    <div className="absolute bottom-4 left-4 z-10 hidden max-w-[280px] rounded-lg border border-navy-700 bg-navy-900/90 p-3 text-xs backdrop-blur sm:block">
      <div className="mb-2 text-slate-400 font-medium">Legend</div>
      <div className="space-y-2">
        <LegendRow
          marker={<span className="inline-block h-3 w-3 rounded-full border-2 border-white bg-teal-500" />}
          title={`Named spots (${spotCount || "..."})`}
          detail="Confirmed public references with named detail panels."
        />
        <LegendRow
          marker={<span className="inline-block h-2.5 w-2.5 rounded-full bg-orange-400" />}
          title={`Candidate segments (${highCandidateCount || "..."})`}
          detail="Exploratory leads only. Treat these as unconfirmed candidates."
        />
        <LegendRow
          marker={<span className="inline-block h-1.5 w-1.5 rounded-full bg-slate-500" />}
          title={`Context coastline (${segmentCount || "..."})`}
          detail="Background scored coastline for regional context, not a named break list."
        />
      </div>
    </div>
  );
}
