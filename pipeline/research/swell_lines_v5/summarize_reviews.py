#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.research.swell_lines_v5 import (  # noqa: E402
    CANDIDATE_SCENES_PATH,
    SCENE_REVIEWS_PATH,
    SUMMARY_PATH,
)
from pipeline.research.swell_lines_v5.signal_validation import (  # noqa: E402
    build_summary,
    load_json,
    load_scene_reviews,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize v5 signal-validation labels.")
    parser.add_argument("--candidates", type=Path, default=CANDIDATE_SCENES_PATH)
    parser.add_argument("--reviews", type=Path, default=SCENE_REVIEWS_PATH)
    parser.add_argument("--output", type=Path, default=SUMMARY_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidates_payload = load_json(args.candidates)
    review_rows = load_scene_reviews(args.reviews)
    summary = build_summary(candidates_payload, review_rows)
    write_json(args.output, summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

