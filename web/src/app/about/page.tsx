import Nav from "@/components/Nav";

export const metadata = {
  title: "About — WaveScout",
  description: "About WaveScout — satellite-based surf discovery for Nova Scotia.",
};

export default function AboutPage() {
  return (
    <>
      <Nav />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
          {/* Hero */}
          <div className="mb-12">
            <div className="text-xs uppercase tracking-[0.18em] text-bone-mute mb-4 font-readout">
              About · Nova Scotia
            </div>
            <h1 className="font-display text-5xl sm:text-6xl font-semibold text-bone mb-5 tracking-tight leading-[1.05]">
              A coastal evidence atlas.
            </h1>
            <p className="text-lg text-bone-dim leading-relaxed max-w-[60ch]">
              WaveScout reads satellite imagery, coastline geometry, and ocean
              data to find where waves break along Nova Scotia&apos;s coast.
              Each claim is paired with the imagery behind it.
            </p>
          </div>

          {/* What it is */}
          <section className="mb-10">
            <h2 className="font-display text-2xl font-semibold text-teal-400 mb-4 tracking-tight">
              What is this?
            </h2>
            <p className="text-bone-dim leading-[1.75] mb-4 max-w-[66ch]">
              WaveScout is a surf discovery tool that analyzes over 16,000
              coastline segments across Nova Scotia using Sentinel-2 satellite
              imagery from the European Space Agency. Across hundreds of
              satellite passes — correlated with swell conditions — it finds
              stretches of coast that behave like surf breaks.
            </p>
            <p className="text-bone-dim leading-[1.75] max-w-[66ch]">
              It&apos;s evidence-based discovery, not wave forecasting. The data
              tells you where waves consistently break and under what conditions
              &mdash; but only your feet in the water confirm if it&apos;s actually
              surfable.
            </p>
          </section>

          {/* How it works summary */}
          <section className="mb-10">
            <h2 className="font-display text-2xl font-semibold text-teal-400 mb-4 tracking-tight">
              The Pipeline
            </h2>
            <div className="space-y-3">
              {[
                {
                  step: "1",
                  title: "Segment the Coastline",
                  desc: "Nova Scotia's coastline is divided into ~16,939 segments (~500m each), each scored on swell exposure, geometry, bathymetry, and road access.",
                },
                {
                  step: "2",
                  title: "Observe from Satellites",
                  desc: "For each segment, we analyze ~120 clear Sentinel-2 scenes. Repeated brightness in the near-infrared band — where calm water looks dark and whitewater looks bright — becomes evidence that waves are breaking.",
                },
                {
                  step: "3",
                  title: "Correlate Evidence with Conditions",
                  desc: "Each observation is joined to swell height, period, and direction. Response patterns — segments that light up on bigger days or turn off when swell is blocked — build into a profile.",
                },
                {
                  step: "4",
                  title: "Score & Validate",
                  desc: "Combine geometry scores with swell profiles and cross-reference against 20 known surf spots for calibration.",
                },
              ].map((item) => (
                <div
                  key={item.step}
                  className="flex gap-4 bg-navy-800/50 rounded-lg p-4 border border-navy-700"
                >
                  <div className="w-8 h-8 rounded-full bg-teal-500/20 text-teal-400 flex items-center justify-center text-sm font-bold shrink-0">
                    {item.step}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-bone">
                      {item.title}
                    </h3>
                    <p className="text-sm text-bone-dim mt-0.5 leading-relaxed">
                      {item.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Data sources */}
          <section className="mb-10">
            <h2 className="font-display text-2xl font-semibold text-teal-400 mb-4 tracking-tight">
              Data Sources
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                {
                  name: "Sentinel-2",
                  org: "ESA / Copernicus",
                  desc: "10m multispectral satellite imagery via Google Earth Engine",
                },
                {
                  name: "Open-Meteo",
                  org: "Marine API",
                  desc: "Swell height, period, and direction for each satellite pass",
                },
                {
                  name: "GEBCO",
                  org: "Bathymetric Chart",
                  desc: "Ocean floor depth for bathymetric gradient scoring",
                },
                {
                  name: "OpenStreetMap",
                  org: "Community",
                  desc: "Coastline geometry, road access data",
                },
              ].map((source) => (
                <div
                  key={source.name}
                  className="bg-navy-800 rounded-lg p-3 border border-navy-700"
                >
                  <div className="text-sm font-semibold text-bone">
                    {source.name}
                  </div>
                  <div className="text-xs text-teal-400/80 font-readout tracking-wide">
                    {source.org}
                  </div>
                  <div className="text-xs text-bone-dim mt-1 leading-relaxed">
                    {source.desc}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Built by */}
          <section className="mb-10">
            <h2 className="font-display text-2xl font-semibold text-teal-400 mb-4 tracking-tight">
              Built By
            </h2>
            <p className="text-bone-dim leading-[1.75] max-w-[66ch]">
              WaveScout is built by{" "}
              <span className="text-bone font-semibold">Graham Mann</span>, a
              surfer and developer based in Nova Scotia. The project started as
              a question: can satellite imagery tell us anything useful about
              where waves break along a rugged, under-explored coastline?
            </p>
            <p className="text-bone-dim leading-[1.75] mt-3 max-w-[66ch]">
              Turns out it can.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="font-display text-2xl font-semibold text-teal-400 mb-4 tracking-tight">
              Scope Boundary
            </h2>
            <p className="text-bone-dim leading-[1.75] max-w-[66ch]">
              WaveScout is a static discovery tool for Nova Scotia. It helps you
              inspect precomputed evidence about where waves may break, but it
              does not provide live forecasts, safety guidance, or access advice.
            </p>
          </section>

          <section className="mb-10">
            <h2 className="font-display text-2xl font-semibold text-teal-400 mb-4 tracking-tight">
              Uncertainty And Safety
            </h2>
            <p className="text-bone-dim leading-[1.75] max-w-[66ch]">
              Evidence quality varies by scene coverage, contamination, and data
              density. A strong score does not mean a break is safe, public,
              working today, or worth surfing in your conditions. Always verify
              access, hazards, tides, and local conditions independently.
            </p>
          </section>

          {/* Footer */}
          <div className="border-t border-navy-700 pt-6 mt-12 text-center text-xs text-bone-mute font-readout tracking-wide">
            Satellite imagery: Copernicus Sentinel-2 (ESA) via Google Earth
            Engine. Marine data: Open-Meteo. Coastline: OpenStreetMap.
          </div>
        </div>
      </main>
    </>
  );
}
