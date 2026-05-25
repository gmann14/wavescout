"""Tests for the V5 swell-line review sheet generator."""
from __future__ import annotations

from pathlib import Path

from pipeline.research.swell_lines_v5.build_review_sheet import (
    REVIEW_LABEL_DEFINITIONS,
    ReviewRow,
    load_review_rows,
    render_review_sheet,
)


CSV_HEADER = (
    "review_id,spot_slug,spot_name,date,source,scene_source,"
    "is_frozen_organized,label,note,rgb_path,annotated_rgb_path,"
    "nir_path,annotated_nir_path"
)


def _write_csv(path: Path, rows: list[str]) -> None:
    path.write_text("\n".join([CSV_HEADER, *rows]) + "\n", encoding="utf-8")


def test_load_review_rows_parses_required_fields(tmp_path: Path) -> None:
    csv = tmp_path / "reviews.csv"
    _write_csv(
        csv,
        [
            "spot-a_2024-01-01,spot-a,Spot A,2024-01-01,frozen_organized,foam,true,,,"
            "images/a/rgb.png,,images/a/nir.png,",
            "spot-b_2024-02-02,spot-b,Spot B,2024-02-02,development_candidate,foam,false,"
            "clear_positive,Looks crisp,images/b/rgb.png,images/b/rgb_ann.png,"
            "images/b/nir.png,images/b/nir_ann.png",
        ],
    )

    rows = load_review_rows(csv)

    assert len(rows) == 2
    assert rows[0].review_id == "spot-a_2024-01-01"
    assert rows[0].spot_slug == "spot-a"
    assert rows[0].is_frozen_organized is True
    assert rows[0].label == ""
    assert rows[1].label == "clear_positive"
    assert rows[1].annotated_rgb_path == "images/b/rgb_ann.png"


def test_render_review_sheet_renders_one_card_per_row(tmp_path: Path) -> None:
    rgb_path = tmp_path / "images" / "rgb.png"
    rgb_path.parent.mkdir(parents=True)
    rgb_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    nir_path = tmp_path / "images" / "nir.png"
    nir_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    rows = [
        ReviewRow(
            review_id="spot-a_2024-01-01",
            spot_slug="spot-a",
            spot_name="Spot A",
            date="2024-01-01",
            source="frozen_organized",
            scene_source="foam",
            is_frozen_organized=True,
            label="",
            note="",
            rgb_path=str(rgb_path),
            annotated_rgb_path="",
            nir_path=str(nir_path),
            annotated_nir_path="",
        ),
        ReviewRow(
            review_id="spot-b_2024-02-02",
            spot_slug="spot-b",
            spot_name="Spot B",
            date="2024-02-02",
            source="development_candidate",
            scene_source="foam",
            is_frozen_organized=False,
            label="clear_positive",
            note="organized lines",
            rgb_path="",
            annotated_rgb_path="",
            nir_path="",
            annotated_nir_path="",
        ),
    ]

    html, warnings = render_review_sheet(rows, out_dir=tmp_path)

    assert html.count("<article") == 2
    for label in REVIEW_LABEL_DEFINITIONS:
        assert label in html
    assert "Spot A" in html
    assert "Spot B" in html
    # frozen organized rows should be marked
    assert "frozen-organized" in html
    # Missing rgb/nir paths must surface as warnings, not crash.
    assert any("spot-b" in w for w in warnings)


def test_render_review_sheet_escapes_csv_content(tmp_path: Path) -> None:
    rows = [
        ReviewRow(
            review_id="evil",
            spot_slug="evil",
            spot_name="<script>alert(1)</script>",
            date="2024-01-01",
            source="frozen_organized",
            scene_source="foam",
            is_frozen_organized=True,
            label="ambiguous",
            note="\"); evil()<",
            rgb_path="",
            annotated_rgb_path="",
            nir_path="",
            annotated_nir_path="",
        )
    ]
    html, _ = render_review_sheet(rows, out_dir=tmp_path)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&quot;); evil()&lt;" in html
    assert "<label>,<note>" not in html
    assert "&lt;label&gt;,&lt;note&gt;" in html


def test_render_review_sheet_groups_by_spot_with_frozen_first(tmp_path: Path) -> None:
    rgb = tmp_path / "rgb.png"
    rgb.write_bytes(b"\x89PNG\r\n\x1a\n")
    rows = [
        ReviewRow(
            review_id="spot-a_dev",
            spot_slug="spot-a",
            spot_name="Spot A",
            date="2024-03-03",
            source="development_candidate",
            scene_source="foam",
            is_frozen_organized=False,
            label="",
            note="",
            rgb_path=str(rgb),
            annotated_rgb_path="",
            nir_path="",
            annotated_nir_path="",
        ),
        ReviewRow(
            review_id="spot-a_frozen",
            spot_slug="spot-a",
            spot_name="Spot A",
            date="2024-01-01",
            source="frozen_organized",
            scene_source="foam",
            is_frozen_organized=True,
            label="",
            note="",
            rgb_path=str(rgb),
            annotated_rgb_path="",
            nir_path="",
            annotated_nir_path="",
        ),
    ]
    html, _ = render_review_sheet(rows, out_dir=tmp_path)
    frozen_idx = html.find("spot-a_frozen")
    dev_idx = html.find("spot-a_dev")
    assert 0 <= frozen_idx < dev_idx, (
        "frozen_organized rows should render before development_candidate rows in the same spot group"
    )
