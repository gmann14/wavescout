# V5 Review Instructions

## What You Need To Do

Work from:

- `pipeline/research/swell_lines_v5/scene_reviews.csv`

Use the local images referenced in each row:

- `rgb_path`
- `nir_path`

Most selected scenes now point at:

- `pipeline/research/swell_lines_v5/review_images/...`

For each row:

1. Look at the scene imagery for that spot/date.
2. Decide whether offshore swell lines in the review area are:
   - `clear_positive`
   - `ambiguous`
   - `clear_negative`
3. Write that value into the `label` column.
4. Add one short note in the `note` column explaining why.

For a browser-friendly contact sheet that opens locally, run:

```bash
venv/bin/python pipeline/research/swell_lines_v5/build_review_sheet.py
```

That writes `pipeline/research/swell_lines_v5/review_sheet.html` (kept
out of git) and reports any rows with missing imagery. The generator
never edits the CSV — it only renders existing rows so you can compare
RGB and NIR scenes side-by-side before typing labels back into the
CSV.

## Label Definitions

- `clear_positive`
  - multiple roughly parallel offshore crest lines are clearly visible
  - the structure looks coherent enough that a detector should plausibly recover it
- `ambiguous`
  - some line-like structure is present, but it is weak, broken, messy, or not a fair detector target
- `clear_negative`
  - no convincing organized offshore crest-line structure is visible

## Review Order

Do these first:

1. The 4 frozen organized scenes
2. The remaining development candidates

The frozen organized scenes are the rows where:

- `source = frozen_organized`

## After You Finish

Run:

```bash
venv/bin/python pipeline/research/swell_lines_v5/summarize_reviews.py
```

That updates:

- `pipeline/research/swell_lines_v5/summary.json`

If you do not want to edit the CSV directly, you can also send me labels in chat as:

```text
spot_slug, date, label, note
```

and I can write them into the review sheet for you.
