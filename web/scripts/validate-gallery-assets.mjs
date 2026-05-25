import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const publicRoot = path.join(webRoot, "public");
const datasetManifestPath = path.join(publicRoot, "data", "dataset-manifest.json");
const collectionSegments = ["gallery", "atlas-gallery"];

let imageDelivery = { mode: "static-public", gallery_url_prefix: null };
if (fs.existsSync(datasetManifestPath)) {
  try {
    const datasetManifest = JSON.parse(fs.readFileSync(datasetManifestPath, "utf8"));
    if (datasetManifest && typeof datasetManifest === "object" && datasetManifest.image_delivery) {
      imageDelivery = datasetManifest.image_delivery;
    }
  } catch (error) {
    console.error(`Failed to read dataset-manifest.json: ${error.message}`);
    process.exit(1);
  }
}

function normalizeGalleryPrefix(prefix) {
  if (prefix == null || prefix === "") return null;
  if (typeof prefix !== "string") {
    throw new Error("image_delivery.gallery_url_prefix must be a string or null");
  }
  const trimmed = prefix.trim();
  if (trimmed.startsWith("//") || !trimmed.startsWith("https://")) {
    throw new Error(`image_delivery.gallery_url_prefix must be an absolute https URL: ${prefix}`);
  }
  return trimmed.replace(/\/+$/, "");
}

function prefixCollectionSegment(prefix) {
  const parsed = new URL(prefix);
  const segments = parsed.pathname.split("/").filter(Boolean);
  const last = segments.at(-1);
  return collectionSegments.includes(last) ? last : null;
}

function replacePrefixCollection(prefix, collection) {
  const current = prefixCollectionSegment(prefix);
  if (!current) return `${prefix}/${collection}`;
  return `${prefix.slice(0, -(current.length + 1))}/${collection}`;
}

function normalizeImageDelivery(raw) {
  const mode = raw?.mode ?? "static-public";
  if (!["static-public", "cdn"].includes(mode)) {
    throw new Error(`dataset-manifest.json image_delivery.mode is unsupported: ${mode}`);
  }
  const prefix = raw?.gallery_url_prefix ?? null;
  if (mode === "static-public") {
    if (prefix != null && prefix !== "") {
      throw new Error("static-public image delivery must not set gallery_url_prefix");
    }
    return { mode: "static-public", gallery_url_prefix: null, allowedRemotePrefixes: [] };
  }
  const normalizedPrefix = normalizeGalleryPrefix(prefix);
  if (!normalizedPrefix) {
    throw new Error("cdn image delivery requires gallery_url_prefix");
  }
  const collection = prefixCollectionSegment(normalizedPrefix);
  const allowedRemotePrefixes = collection
    ? collectionSegments.map((segment) => replacePrefixCollection(normalizedPrefix, segment))
    : collectionSegments.map((segment) => `${normalizedPrefix}/${segment}`);
  return { mode: "cdn", gallery_url_prefix: normalizedPrefix, allowedRemotePrefixes };
}

try {
  imageDelivery = normalizeImageDelivery(imageDelivery);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}

const manifests = [
  { label: "gallery.json", file: path.join(publicRoot, "data", "gallery.json") },
  { label: "atlas/gallery.json", file: path.join(publicRoot, "data", "atlas", "gallery.json") },
];

const imageKeys = ["rgb_path", "nir_path", "annotated_rgb_path", "annotated_nir_path"];
const failures = [];
let localChecked = 0;
let remoteSkipped = 0;

function publicAssetPath(webPath, label) {
  const resolved = path.resolve(publicRoot, `.${webPath}`);
  const relative = path.relative(publicRoot, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`${label} image path escapes public/: ${webPath}`);
  }
  return resolved;
}

function classifyImagePath(webPath, label) {
  if (typeof webPath !== "string") {
    throw new Error(`${label} image path must be a string or null`);
  }
  if (webPath.startsWith("//")) {
    throw new Error(`${label} protocol-relative URLs are not allowed: ${webPath}`);
  }
  if (webPath.startsWith("https://")) {
    return "remote-https";
  }
  if (webPath.startsWith("/")) {
    return "local";
  }
  throw new Error(`${label} image path has unsupported scheme or shape: ${webPath}`);
}

for (const manifest of manifests) {
  if (!fs.existsSync(manifest.file)) {
    continue;
  }

  const payload = JSON.parse(fs.readFileSync(manifest.file, "utf8"));
  const entries = payload.spots ?? payload.sections ?? [];
  for (const entry of entries) {
    const slug = entry.slug ?? entry.section_id ?? "unknown";
    for (const scene of entry.scenes ?? []) {
      for (const key of imageKeys) {
        const webPath = scene[key];
        if (!webPath) {
          continue;
        }

        const kind = classifyImagePath(webPath, manifest.label);
        if (kind === "remote-https") {
          if (imageDelivery.mode !== "cdn") {
            failures.push(
              `${manifest.label} ${slug}:${scene.date ?? "unknown-date"} ${key} uses https URL but dataset image_delivery.mode is not 'cdn': ${webPath}`,
            );
            continue;
          }
          if (!imageDelivery.allowedRemotePrefixes.some((prefix) => webPath === prefix || webPath.startsWith(`${prefix}/`))) {
            failures.push(
              `${manifest.label} ${slug}:${scene.date ?? "unknown-date"} ${key} is outside configured gallery_url_prefix ${imageDelivery.gallery_url_prefix}: ${webPath}`,
            );
            continue;
          }
          remoteSkipped += 1;
          continue;
        }

        localChecked += 1;
        const assetPath = publicAssetPath(webPath, manifest.label);
        if (!fs.existsSync(assetPath) || !fs.statSync(assetPath).isFile()) {
          failures.push(`${manifest.label} ${slug}:${scene.date ?? "unknown-date"} ${key} -> ${webPath}`);
        }
      }
    }
  }
}

if (failures.length > 0) {
  console.error("Gallery asset validation failed.");
  for (const failure of failures.slice(0, 20)) {
    console.error(`- ${failure}`);
  }
  if (failures.length > 20) {
    console.error(`- +${failures.length - 20} more`);
  }
  process.exit(1);
}

const remoteSuffix = remoteSkipped > 0 ? ` (skipped ${remoteSkipped} remote https URLs in cdn mode)` : "";
console.log(`Gallery asset validation passed (${localChecked} local paths checked)${remoteSuffix}.`);
