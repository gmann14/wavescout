import { Suspense } from "react";
import Nav from "@/components/Nav";
import CompareView from "@/components/CompareView";

export const metadata = {
  title: "Compare Spots — WaveScout",
  description:
    "Compare multiple surf spots on the same satellite acquisition date to see which spots fire on which conditions.",
};

export default function ComparePage() {
  return (
    <>
      <Nav />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
          <div className="mb-10">
            <div className="text-xs uppercase tracking-[0.18em] text-bone-mute mb-4 font-readout">
              Compare · Same acquisition date
            </div>
            <h1 className="font-display text-4xl sm:text-5xl font-semibold text-bone mb-4 tracking-tight leading-[1.08]">
              Cross-spot comparison.
            </h1>
            <p className="text-lg text-bone-dim leading-relaxed max-w-[60ch]">
              Same satellite pass, multiple spots. See which breaks fire on the
              same swell conditions.
            </p>
          </div>
          <Suspense
            fallback={
              <div className="text-center py-16 text-slate-500">
                Loading comparison data...
              </div>
            }
          >
            <CompareView />
          </Suspense>
        </div>
      </main>
    </>
  );
}
