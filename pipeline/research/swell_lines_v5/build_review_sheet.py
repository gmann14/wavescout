#!/usr/bin/env python3
"""Generate a static HTML review sheet from ``scene_reviews.csv``.

The generator never changes labels: it only renders existing rows in a
browser-friendly layout grouped by spot. The resulting HTML opens
directly from the repo checkout so reviewers can compare the RGB and
NIR scenes side-by-side and type their labels back into the CSV.

Usage::

    python pipeline/research/swell_lines_v5/build_review_sheet.py \
        --out pipeline/research/swell_lines_v5/review_sheet.html
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass, field, fields
from html import escape
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.research.swell_lines_v5 import (  # noqa: E402
    SCENE_REVIEWS_PATH,
)


REVIEW_LABEL_DEFINITIONS: dict[str, str] = {
    "clear_positive": (
        "Multiple roughly parallel offshore crest lines are clearly visible; "
        "structure looks coherent enough that a detector should plausibly recover it."
    ),
    "ambiguous": (
        "Some line-like structure is present, but it is weak, broken, messy, "
        "or not a fair detector target."
    ),
    "clear_negative": (
        "No convincing organized offshore crest-line structure is visible."
    ),
}


@dataclass
class ReviewRow:
    review_id: str
    spot_slug: str
    spot_name: str
    date: str
    source: str
    scene_source: str
    is_frozen_organized: bool
    label: str
    note: str
    rgb_path: str
    annotated_rgb_path: str
    nir_path: str
    annotated_nir_path: str


REQUIRED_COLUMNS: tuple[str, ...] = tuple(f.name for f in fields(ReviewRow))


def _coerce_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "t"}


def load_review_rows(csv_path: Path) -> list[ReviewRow]:
    """Load review rows from a CSV file."""
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"{csv_path} missing required columns: {', '.join(missing)}"
            )
        rows: list[ReviewRow] = []
        for raw in reader:
            rows.append(
                ReviewRow(
                    review_id=(raw.get("review_id") or "").strip(),
                    spot_slug=(raw.get("spot_slug") or "").strip(),
                    spot_name=(raw.get("spot_name") or "").strip(),
                    date=(raw.get("date") or "").strip(),
                    source=(raw.get("source") or "").strip(),
                    scene_source=(raw.get("scene_source") or "").strip(),
                    is_frozen_organized=_coerce_bool(
                        raw.get("is_frozen_organized") or ""
                    ),
                    label=(raw.get("label") or "").strip(),
                    note=(raw.get("note") or "").strip(),
                    rgb_path=(raw.get("rgb_path") or "").strip(),
                    annotated_rgb_path=(raw.get("annotated_rgb_path") or "").strip(),
                    nir_path=(raw.get("nir_path") or "").strip(),
                    annotated_nir_path=(raw.get("annotated_nir_path") or "").strip(),
                )
            )
        return rows


def _resolve_image(
    row_path: str, repo_root: Path, out_dir: Path
) -> tuple[str | None, str | None]:
    """Return ``(href, warning)`` for an image referenced from the review CSV.

    Paths in the CSV are repo-root-relative. The HTML is opened from
    ``out_dir`` so we emit a relative URL that points back to the
    actual file when possible. If the file is missing, ``href`` is
    ``None`` and a warning string is returned instead.
    """
    if not row_path:
        return None, None
    absolute = (repo_root / row_path).resolve()
    if not absolute.is_file():
        return None, f"missing image: {row_path}"
    try:
        rel = os.path.relpath(absolute, start=out_dir.resolve())
    except ValueError:
        return absolute.as_uri(), None
    return rel.replace(os.sep, "/"), None


def _group_rows(rows: Iterable[ReviewRow]) -> dict[str, list[ReviewRow]]:
    groups: dict[str, list[ReviewRow]] = {}
    for row in rows:
        groups.setdefault(row.spot_slug, []).append(row)
    for slug, items in groups.items():
        # Frozen-organized scenes first within each spot, then by date.
        items.sort(key=lambda r: (0 if r.is_frozen_organized else 1, r.date))
    return groups


def render_review_sheet(
    rows: list[ReviewRow],
    *,
    out_dir: Path,
    repo_root: Path = ROOT,
) -> tuple[str, list[str]]:
    """Render the review sheet HTML and return ``(html, warnings)``."""
    warnings: list[str] = []
    groups = _group_rows(rows)

    label_definition_html = "\n".join(
        f"<dt>{escape(label)}</dt><dd>{escape(definition)}</dd>"
        for label, definition in REVIEW_LABEL_DEFINITIONS.items()
    )

    spot_sections: list[str] = []
    for spot_slug in sorted(groups):
        spot_rows = groups[spot_slug]
        spot_name = spot_rows[0].spot_name or spot_slug
        article_blocks: list[str] = []
        for row in spot_rows:
            rgb_href, rgb_warn = _resolve_image(row.rgb_path, repo_root, out_dir)
            if rgb_warn:
                warnings.append(f"{row.spot_slug}:{row.date}: {rgb_warn}")
            elif not row.rgb_path:
                warnings.append(
                    f"{row.spot_slug}:{row.date}: no rgb_path set in CSV"
                )
            nir_href, nir_warn = _resolve_image(row.nir_path, repo_root, out_dir)
            if nir_warn:
                warnings.append(f"{row.spot_slug}:{row.date}: {nir_warn}")
            elif not row.nir_path:
                warnings.append(
                    f"{row.spot_slug}:{row.date}: no nir_path set in CSV"
                )
            annotated_rgb_href, _ = _resolve_image(
                row.annotated_rgb_path, repo_root, out_dir
            )
            annotated_nir_href, _ = _resolve_image(
                row.annotated_nir_path, repo_root, out_dir
            )

            frozen_class = " frozen-organized" if row.is_frozen_organized else ""
            frozen_badge = (
                "<span class=\"badge\">frozen-organized</span>"
                if row.is_frozen_organized
                else ""
            )

            images_html_parts: list[str] = []
            if rgb_href:
                images_html_parts.append(
                    f'<figure><img src="{escape(rgb_href)}" alt="RGB"/>'
                    f'<figcaption>RGB</figcaption></figure>'
                )
            if nir_href:
                images_html_parts.append(
                    f'<figure><img src="{escape(nir_href)}" alt="NIR"/>'
                    f'<figcaption>NIR</figcaption></figure>'
                )
            if not images_html_parts:
                images_html_parts.append(
                    '<p class="missing">No imagery available for this row.</p>'
                )

            annotated_links: list[str] = []
            if annotated_rgb_href:
                annotated_links.append(
                    f'<a href="{escape(annotated_rgb_href)}">annotated RGB</a>'
                )
            if annotated_nir_href:
                annotated_links.append(
                    f'<a href="{escape(annotated_nir_href)}">annotated NIR</a>'
                )
            annotated_html = (
                "<p>Annotated: " + " · ".join(annotated_links) + "</p>"
                if annotated_links
                else ""
            )

            csv_patch = (
                f"{escape(row.spot_slug)},{escape(row.date)},"
                f"{escape('<label>')},{escape('<note>')}"
            )
            article_blocks.append(
                f'<article id="{escape(row.review_id)}" class="scene{frozen_class}">'
                f'<header><h3>{escape(row.date)} — {escape(row.spot_name)}</h3>'
                f"{frozen_badge}"
                f'<p class="meta">source: {escape(row.source)}</p>'
                f'<p class="meta">scene_source: {escape(row.scene_source)}</p>'
                f'<p class="meta">current label: {escape(row.label) or "—"}</p>'
                f'<p class="meta">note: {escape(row.note) or "—"}</p>'
                "</header>"
                f'<div class="images">{"".join(images_html_parts)}</div>'
                f"{annotated_html}"
                f'<details><summary>CSV patch</summary>'
                f"<pre>{csv_patch}</pre></details>"
                "</article>"
            )

        spot_sections.append(
            f'<section class="spot" id="spot-{escape(spot_slug)}">'
            f"<h2>{escape(spot_name)} <small>({escape(spot_slug)})</small></h2>"
            f'{"".join(article_blocks)}'
            "</section>"
        )

    warnings_html = ""
    if warnings:
        items = "".join(f"<li>{escape(w)}</li>" for w in warnings)
        warnings_html = f'<aside class="warnings"><h2>Warnings</h2><ul>{items}</ul></aside>'

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>V5 Swell-Line Review Sheet</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; }}
section.spot {{ margin: 2rem 0; border-top: 1px solid #ccc; padding-top: 1rem; }}
article.scene {{ margin: 1.5rem 0; padding: 1rem; border: 1px solid #ddd; border-radius: 6px; }}
article.scene.frozen-organized {{ background: #f5fbff; border-color: #bcd8e7; }}
article.scene header h3 {{ margin: 0; font-size: 1.05rem; }}
.badge {{ display: inline-block; background: #2a6f97; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 0.75rem; margin-left: .5rem; }}
.meta {{ margin: .15rem 0; font-size: .85rem; color: #444; }}
.images {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: .75rem; }}
.images figure {{ margin: 0; }}
.images img {{ width: 100%; height: auto; display: block; border: 1px solid #eee; }}
.images figcaption {{ text-align: center; font-size: .8rem; color: #666; }}
.missing {{ color: #b94a48; font-style: italic; }}
aside.warnings {{ background: #fff8e1; border: 1px solid #f0c36d; padding: 1rem; margin: 2rem 0; }}
details > summary {{ cursor: pointer; color: #2a6f97; }}
dl.labels dt {{ font-weight: bold; margin-top: .5rem; }}
dl.labels dd {{ margin: 0 0 .5rem 1.25rem; }}
</style>
</head>
<body>
<h1>V5 Swell-Line Review Sheet</h1>
<section class="instructions">
<h2>Label Definitions</h2>
<dl class="labels">
{label_definition_html}
</dl>
<p>Generated from <code>scene_reviews.csv</code>. To record labels,
edit the CSV directly with the <code>label</code> and <code>note</code>
columns. After updating labels run
<code>python pipeline/research/swell_lines_v5/summarize_reviews.py</code>.
</p>
</section>
{warnings_html}
{"".join(spot_sections)}
</body>
</html>
"""
    return document, warnings


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render scene_reviews.csv as a static review sheet."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=SCENE_REVIEWS_PATH,
        help="Path to scene_reviews.csv.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "review_sheet.html",
        help="Output HTML path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = load_review_rows(args.csv)
    out_path: Path = args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    document, warnings = render_review_sheet(rows, out_dir=out_path.parent)
    out_path.write_text(document, encoding="utf-8")
    print(f"Wrote {out_path} ({len(rows)} rows)")
    for warning in warnings:
        print(f"  warning: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
