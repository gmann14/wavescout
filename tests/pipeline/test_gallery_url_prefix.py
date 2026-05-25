"""Tests for the gallery image URL helper used by web data builders."""
from __future__ import annotations

import pytest

from pipeline.scripts._public_dataset import (
    allowed_cdn_url_prefixes,
    image_delivery_metadata,
    normalize_gallery_url_prefix,
    public_gallery_url,
)


def test_public_gallery_url_passthrough_when_no_prefix() -> None:
    assert (
        public_gallery_url("/gallery/foo/bar.png", prefix=None)
        == "/gallery/foo/bar.png"
    )


def test_public_gallery_url_emits_cdn_url_when_prefix_supplied() -> None:
    assert (
        public_gallery_url(
            "/gallery/foo/bar.png", prefix="https://cdn.example.test/gallery"
        )
        == "https://cdn.example.test/gallery/foo/bar.png"
    )


def test_public_gallery_url_normalizes_double_slashes() -> None:
    assert (
        public_gallery_url(
            "/gallery/foo/bar.png", prefix="https://cdn.example.test/gallery/"
        )
        == "https://cdn.example.test/gallery/foo/bar.png"
    )


def test_public_gallery_url_handles_atlas_gallery_paths() -> None:
    assert (
        public_gallery_url(
            "/atlas-gallery/section/baz.png",
            prefix="https://cdn.example.test",
        )
        == "https://cdn.example.test/atlas-gallery/section/baz.png"
    )


def test_public_gallery_url_treats_gallery_and_atlas_prefixes_as_siblings() -> None:
    assert (
        public_gallery_url(
            "/atlas-gallery/section/baz.png",
            prefix="https://cdn.example.test/gallery",
        )
        == "https://cdn.example.test/atlas-gallery/section/baz.png"
    )
    assert (
        public_gallery_url(
            "/gallery/foo/bar.png",
            prefix="https://cdn.example.test/atlas-gallery",
        )
        == "https://cdn.example.test/gallery/foo/bar.png"
    )


def test_allowed_cdn_url_prefixes_include_gallery_and_atlas_siblings() -> None:
    assert allowed_cdn_url_prefixes("https://cdn.example.test/assets") == (
        "https://cdn.example.test/assets/gallery",
        "https://cdn.example.test/assets/atlas-gallery",
    )
    assert allowed_cdn_url_prefixes("https://cdn.example.test/gallery") == (
        "https://cdn.example.test/gallery",
        "https://cdn.example.test/atlas-gallery",
    )


def test_public_gallery_url_returns_none_for_null_paths() -> None:
    assert public_gallery_url(None, prefix=None) is None
    assert public_gallery_url(None, prefix="https://cdn.example.test") is None


def test_normalize_gallery_url_prefix_requires_https() -> None:
    assert normalize_gallery_url_prefix(None) is None
    assert normalize_gallery_url_prefix("") is None
    assert (
        normalize_gallery_url_prefix("https://cdn.example.test/gallery/")
        == "https://cdn.example.test/gallery"
    )
    with pytest.raises(ValueError):
        normalize_gallery_url_prefix("http://cdn.example.test")
    with pytest.raises(ValueError):
        normalize_gallery_url_prefix("//cdn.example.test")
    with pytest.raises(ValueError):
        normalize_gallery_url_prefix("ftp://cdn.example.test")


def test_image_delivery_metadata_defaults_to_static_public() -> None:
    metadata = image_delivery_metadata(prefix=None)
    assert metadata == {"mode": "static-public", "gallery_url_prefix": None}


def test_image_delivery_metadata_records_cdn_prefix() -> None:
    metadata = image_delivery_metadata(prefix="https://cdn.example.test/gallery")
    assert metadata == {
        "mode": "cdn",
        "gallery_url_prefix": "https://cdn.example.test/gallery",
    }
