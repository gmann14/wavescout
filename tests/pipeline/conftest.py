from __future__ import annotations

import json
from pathlib import Path

import pytest


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def load_fixture(name: str) -> dict:
    with (FIXTURES / name).open() as handle:
        return json.load(handle)


@pytest.fixture
def dataset_manifest() -> dict:
    return load_fixture("dataset-manifest.json")


@pytest.fixture
def spots_payload() -> dict:
    return load_fixture("spots.json")


@pytest.fixture
def segments_high_payload() -> dict:
    return load_fixture("segments-high.json")


@pytest.fixture
def gallery_payload() -> dict:
    return load_fixture("gallery.json")
