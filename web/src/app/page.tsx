import Nav from "@/components/Nav";
import MapView from "@/components/MapView";

export default function HomePage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", width: "100%" }}>
      <Nav />
      <div style={{ flex: 1, position: "relative", minHeight: 0 }}>
        <MapView />
      </div>
    </div>
  );
}
