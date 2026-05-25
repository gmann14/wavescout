"""Smoke tests for dependencies required by the checked-in test suite.

These tests fail fast when the active Python environment is missing
packages that ``requirements.txt`` already declares. The release
readiness checklist documents Python 3.12 with ``pip install -r
requirements.txt`` as the supported setup; this test pins that
assumption so a partial environment cannot silently skip coverage.
"""
from __future__ import annotations

import importlib

import pytest

REQUIRED_FOR_TESTS = (
    # Required to import pipeline.research.swell_lines_v4.detect at
    # test collection time.
    "pywt",
    "numpy",
    "scipy",
)


@pytest.mark.parametrize("module_name", REQUIRED_FOR_TESTS)
def test_required_import_for_test_suite(module_name: str) -> None:
    importlib.import_module(module_name)
