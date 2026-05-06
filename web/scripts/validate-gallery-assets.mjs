import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const publicRoot = path.join(webRoot, "public");

const manifests = [
  { label: "gallery.json", file: path.join(publicRoot, "data", "gallery.json") },
  { label: "atlas/gallery.json", file: path.join(publicRoot, "data", "atlas", "gallery.json") },
];

const imageKeys = ["rgb_path", "nir_path", "annotated_rgb_path", "annotated_nir_path"];
const failures = [];
let checked = 0;

function publicAssetPath(webPath, label) {
  if (typeof webPath !== "string") {
    throw new Error(`${label} image path must be a string or null`);
  }
  if (!webPath.startsWith("/")) {
    throw new Error(`${label} image path must be web-root-relative: ${webPath}`);
  }

  const resolved = path.resolve(publicRoot, `.${webPath}`);
  const relative = path.relative(publicRoot, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`${label} image path escapes public/: ${webPath}`);
  }
  return resolved;
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

        checked += 1;
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

console.log(`Gallery asset validation passed (${checked} paths checked).`);
