#!/usr/bin/env python3
"""Validate the current public web dataset."""

from __future__ import annotations

import argparse

from _public_dataset import validate_public_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Enforce normalized public contract fields.")
    parser.add_argument("--require-atlas", action="store_true", help="Require atlas artifacts in the dataset.")
    args = parser.parse_args()

    validate_public_dataset(strict=args.strict, require_atlas=args.require_atlas)
    print("Public dataset validation passed.")


if __name__ == "__main__":
    main()
