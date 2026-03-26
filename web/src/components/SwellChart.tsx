"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";
import type { SwellProfile } from "@/types";

// Swell bin sort order
const BIN_ORDER = [
  "0.0-0.5m",
  "0.5-1.0m",
  "1.0-1.5m",
  "1.5-2.0m",
  "2.0-2.5m",
  "2.5-3.0m",
  "3.0-4.0m",
  "4.0-5.0m",
  "5.0-8.0m",
];

interface Props {
  profile: SwellProfile;
}

export default function SwellChart({ profile }: Props) {
  const data = BIN_ORDER.filter((bin) => bin in profile.swell_bins).map(
    (bin) => ({
      bin,
      label: bin.replace("m", ""),
      foam: Math.round(profile.swell_bins[bin] * 100),
    })
  );

  if (data.length === 0) return null;

  const bestBin = profile.optimal_range?.best_bin;

  return (
    <div className="w-full h-48">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
          <XAxis
            dataKey="label"
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={{ stroke: "#1e2d4d" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `${v}%`}
            domain={[0, "auto"]}
          />
          <Tooltip
            contentStyle={{
              background: "#162038",
              border: "1px solid #1e2d4d",
              borderRadius: 6,
              color: "#e2e8f0",
              fontSize: 13,
            }}
            formatter={(value) => [`${value}% foam`, "Avg foam"]}
            labelFormatter={(label) => `Swell: ${label}m`}
          />
          {profile.turn_on_threshold_m != null && (
            <ReferenceLine
              x={data.findIndex(
                (d) =>
                  parseFloat(d.bin.split("-")[0]) <=
                    profile.turn_on_threshold_m! &&
                  parseFloat(d.bin.split("-")[1]) >
                    profile.turn_on_threshold_m!
              )}
              stroke="#f97316"
              strokeDasharray="3 3"
              label=""
            />
          )}
          <Bar dataKey="foam" radius={[4, 4, 0, 0]} maxBarSize={40}>
            {data.map((entry) => (
              <Cell
                key={entry.bin}
                fill={entry.bin === bestBin ? "#14b8a6" : "#1e2d4d"}
                stroke={entry.bin === bestBin ? "#2dd4bf" : "#2a3f6b"}
                strokeWidth={1}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
