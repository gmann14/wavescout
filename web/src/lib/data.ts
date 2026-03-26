import type {
  SpotsGeoJSON,
  SegmentsGeoJSON,
  SpotDetail,
  GalleryManifest,
} from "@/types";

const DATA_BASE = "/data";

export async function loadSpots(): Promise<SpotsGeoJSON> {
  const res = await fetch(`${DATA_BASE}/spots.json`);
  return res.json();
}

export async function loadSegmentsHigh(): Promise<SegmentsGeoJSON> {
  const res = await fetch(`${DATA_BASE}/segments-high.json`);
  return res.json();
}

export async function loadSegmentsAll(): Promise<SegmentsGeoJSON> {
  const res = await fetch(`${DATA_BASE}/segments-all.json`);
  return res.json();
}

export async function loadSpotDetail(slug: string): Promise<SpotDetail> {
  const res = await fetch(`${DATA_BASE}/spots/${slug}.json`);
  return res.json();
}

export async function loadGallery(): Promise<GalleryManifest> {
  const res = await fetch(`${DATA_BASE}/gallery.json`);
  return res.json();
}
