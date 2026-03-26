import Nav from "@/components/Nav";
import MapWrapper from "@/components/MapWrapper";

export default function HomePage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", width: "100%" }}>
      <Nav />
      <div style={{ flex: 1, position: "relative", minHeight: 0 }}>
        <MapWrapper />
      </div>
    </div>
  );
}
