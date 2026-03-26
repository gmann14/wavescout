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
          <div className="mb-10">
            <h1 className="text-3xl font-bold text-white mb-3">
              About WaveScout
            </h1>
            <p className="text-lg text-slate-400 leading-relaxed">
              Finding surf spots from space. WaveScout uses satellite imagery,
              coastline geometry, and ocean data to discover where waves break
              along Nova Scotia&apos;s coast.
            </p>
          </div>

          {/* What it is */}
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-teal-400 mb-3">
              What is this?
            </h2>
            <p className="text-slate-400 leading-relaxed mb-3">
              WaveScout is a surf discovery tool that analyzes over 16,000
              coastline segments across Nova Scotia using Sentinel-2 satellite
              imagery from the European Space Agency. By detecting foam and
              whitewater in the near-infrared band, then correlating with swell
              conditions across hundreds of satellite passes, we can identify
              stretches of coast that behave like surf breaks.
            </p>
            <p className="text-slate-400 leading-relaxed">
              It&apos;s evidence-based discovery, not wave forecasting. The data
              tells you where waves consistently break and under what conditions
              &mdash; but only your feet in the water confirm if it&apos;s actually
              surfable.
            </p>
          </section>

          {/* How it works summary */}
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-teal-400 mb-3">
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
                  title: "Detect Foam via NIR",
                  desc: "For each segment, we analyze ~120 clear Sentinel-2 scenes using the near-infrared band. Water absorbs NIR (black), foam reflects it (bright white).",
                },
                {
                  step: "3",
                  title: "Build Swell Profiles",
                  desc: "By correlating foam detection with swell conditions, we build response curves: turn-on threshold, optimal range, and blow-out point.",
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
                    <h3 className="text-sm font-medium text-slate-200">
                      {item.title}
                    </h3>
                    <p className="text-sm text-slate-400 mt-0.5">
                      {item.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Data sources */}
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-teal-400 mb-3">
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
                  <div className="text-sm font-medium text-slate-200">
                    {source.name}
                  </div>
                  <div className="text-xs text-teal-400/80">{source.org}</div>
                  <div className="text-xs text-slate-500 mt-1">
                    {source.desc}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Built by */}
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-teal-400 mb-3">
              Built By
            </h2>
            <p className="text-slate-400 leading-relaxed">
              WaveScout is built by{" "}
              <span className="text-white font-medium">Graham Mann</span>, a
              surfer and developer based in Nova Scotia. The project started as
              a question: can satellite imagery tell us anything useful about
              where waves break along a rugged, under-explored coastline?
            </p>
            <p className="text-slate-400 leading-relaxed mt-3">
              Turns out it can.
            </p>
          </section>

          {/* Footer */}
          <div className="border-t border-navy-700 pt-6 mt-12 text-center text-xs text-slate-600">
            Satellite imagery: Copernicus Sentinel-2 (ESA) via Google Earth
            Engine. Marine data: Open-Meteo. Coastline: OpenStreetMap.
          </div>
        </div>
      </main>
    </>
  );
}
