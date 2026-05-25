"""Tests for the dataset validator's handling of remote gallery URLs."""
from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.scripts._public_dataset import validate_gallery_asset_paths


def _payload(rgb_path: str) -> dict:
    return {
        "spots": [
            {
                "slug": "demo",
                "scenes": [
                    {
                        "date": "2024-01-01",
                        "rgb_path": rgb_path,
                        "nir_path": None,
                    }
                ],
            }
        ]
    }


def test_remote_https_allowed_when_image_delivery_is_cdn(tmp_path: Path) -> None:
    payload = _payload("https://cdn.example.test/gallery/demo/x.png")
    public_root = tmp_path / "public"
    public_root.mkdir()

    validate_gallery_asset_paths(
        payload,
        public_root=public_root,
        label="gallery.json",
        image_delivery={
            "mode": "cdn",
            "gallery_url_prefix": "https://cdn.example.test/gallery",
        },
    )


def test_remote_https_must_match_configured_cdn_prefix(tmp_path: Path) -> None:
    payload = _payload("https://other.example.test/gallery/demo/x.png")
    public_root = tmp_path / "public"
    public_root.mkdir()

    with pytest.raises(ValueError, match="outside configured"):
        validate_gallery_asset_paths(
            payload,
            public_root=public_root,
            label="gallery.json",
            image_delivery={
                "mode": "cdn",
                "gallery_url_prefix": "https://cdn.example.test/gallery",
            },
        )


def test_cdn_mode_requires_valid_gallery_url_prefix(tmp_path: Path) -> None:
    payload = _payload("https://cdn.example.test/gallery/demo/x.png")
    public_root = tmp_path / "public"
    public_root.mkdir()

    with pytest.raises(ValueError, match="requires gallery_url_prefix"):
        validate_gallery_asset_paths(
            payload,
            public_root=public_root,
            label="gallery.json",
            image_delivery={"mode": "cdn", "gallery_url_prefix": None},
        )
    with pytest.raises(ValueError, match="https"):
        validate_gallery_asset_paths(
            payload,
            public_root=public_root,
            label="gallery.json",
            image_delivery={
                "mode": "cdn",
                "gallery_url_prefix": "http://cdn.example.test/gallery",
            },
        )


def test_static_public_mode_rejects_gallery_url_prefix(tmp_path: Path) -> None:
    payload = _payload("/gallery/demo/x.png")
    public_root = tmp_path / "public"
    asset = public_root / "gallery" / "demo" / "x.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"\x89PNG\r\n\x1a\n")

    with pytest.raises(ValueError, match="must not set"):
        validate_gallery_asset_paths(
            payload,
            public_root=public_root,
            label="gallery.json",
            image_delivery={
                "mode": "static-public",
                "gallery_url_prefix": "https://cdn.example.test/gallery",
            },
        )


def test_remote_https_rejected_without_image_delivery_cdn(tmp_path: Path) -> None:
    payload = _payload("https://cdn.example.test/gallery/demo/x.png")
    public_root = tmp_path / "public"
    public_root.mkdir()

    with pytest.raises(ValueError, match="cdn"):
        validate_gallery_asset_paths(
            payload, public_root=public_root, label="gallery.json"
        )


def test_remote_http_rejected_even_in_cdn_mode(tmp_path: Path) -> None:
    payload = _payload("http://cdn.example.test/gallery/demo/x.png")
    public_root = tmp_path / "public"
    public_root.mkdir()

    with pytest.raises(ValueError):
        validate_gallery_asset_paths(
            payload,
            public_root=public_root,
            label="gallery.json",
            image_delivery={
                "mode": "cdn",
                "gallery_url_prefix": "https://cdn.example.test/gallery",
            },
        )


def test_unsafe_schemes_always_rejected(tmp_path: Path) -> None:
    public_root = tmp_path / "public"
    public_root.mkdir()
    for unsafe in [
        "file:///etc/passwd",
        "javascript:alert(1)",
        "//cdn.example.test/gallery/demo/x.png",
    ]:
        with pytest.raises(ValueError):
            validate_gallery_asset_paths(
                _payload(unsafe),
                public_root=public_root,
                label="gallery.json",
                image_delivery={
                    "mode": "cdn",
                    "gallery_url_prefix": "https://cdn.example.test/gallery",
                },
            )


def test_local_paths_still_checked_against_disk(tmp_path: Path) -> None:
    payload = _payload("/gallery/demo/x.png")
    public_root = tmp_path / "public"
    public_root.mkdir()

    with pytest.raises(ValueError, match="missing"):
        validate_gallery_asset_paths(
            payload, public_root=public_root, label="gallery.json"
        )

    # Now create the file and re-validate.
    asset = public_root / "gallery" / "demo" / "x.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"\x89PNG\r\n\x1a\n")
    validate_gallery_asset_paths(
        payload, public_root=public_root, label="gallery.json"
    )


def test_mixed_local_and_remote_validated_consistently(tmp_path: Path) -> None:
    public_root = tmp_path / "public"
    asset = public_root / "gallery" / "demo" / "x.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"\x89PNG\r\n\x1a\n")

    payload = {
        "spots": [
            {
                "slug": "demo",
                "scenes": [
                    {
                        "date": "2024-01-01",
                        "rgb_path": "/gallery/demo/x.png",
                        "nir_path": "https://cdn.example.test/gallery/demo/x.png",
                    }
                ],
            }
        ]
    }

    validate_gallery_asset_paths(
        payload,
        public_root=public_root,
        label="gallery.json",
        image_delivery={
            "mode": "cdn",
            "gallery_url_prefix": "https://cdn.example.test/gallery",
        },
    )
