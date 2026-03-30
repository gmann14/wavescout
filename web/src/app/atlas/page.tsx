import Nav from "@/components/Nav";
import AtlasMap from "@/components/AtlasMap";

export const metadata = {
  title: "Coastline Atlas — WaveScout",
  description:
    "Browse the entire Nova Scotia coastline in ~3km sections. Each section is scored by wave potential and includes satellite imagery across swell conditions.",
};

export default function AtlasPage() {
  return (
    <div
      style={{ display: "flex", flexDirection: "column", height: "100vh", width: "100%" }}
    >
      <Nav />
      <div style={{ flex: 1, position: "relative", minHeight: 0 }}>
        <AtlasMap />
      </div>
    </div>
  );
}
