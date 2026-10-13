# Data Model: PDF Report Redesign

No persisted data changes. These are in-memory and static structures only.

## GiftGuidance (static, `app/data/spiritual_gift_guidance.py`)

`GIFT_GUIDANCE: dict[str, GiftGuidance]`, keyed by gift slug (the keys of `app.core.spiritual_gifts_map.MAP`, 24 entries).

| Field | Type | Rules |
|---|---|---|
| `scriptures` | `list[str]` | 2–3 references, e.g. `"Romans 12:8"`. References only, no quoted verse text |
| `ways_to_serve` | `list[str]` | ≥ 3 short imperative sentences, each ≤ 120 chars |
| `reflection` | `str` | One question ending in `?` |

Validation (test): the key set equals the `MAP` key set, and every entry meets the rules above.

## Gift score inputs (existing, `Assessment.scores` for category `spiritual_gifts`)

- `all_scores: [{gift: display_name, score: int 0–12}]`, already sorted by score descending, then name.
- `top_gifts_truncated` (≤ 3), `top_gifts_expanded` (ties at 3rd), `rank_meta.third_place_score`.

Derived per gift for rendering:
- `slug` (via `display_to_slug`)
- `rank` (1-based position in `all_scores`)
- `band`: `strongest` (≥ 9), `developing` (5–8) or `less_evident` (≤ 4)
- `is_top`: in `top_gifts_truncated`
- `is_tied_third`: in expanded but not truncated
- `summary` and `definition` (from `defs_map[slug]`)
- `guidance` (from `GIFT_GUIDANCE[slug]`)

## Gift definitions input (existing)

`defs_map: dict[slug, {display_name, short_summary, full_definition}]`, built in the routes from `SpiritualGiftDefinition` for the assessment's version.

## Mentor report context (existing)

The output of `build_report_context` is unchanged. The PDF reads the same keys it reads today:
- headline: `apprentice_name`, `submitted_date`, `overall_mc_percent`, `knowledge_band`
- strengths and gaps: `top_strengths`, `top_gaps`
- `categories`, `knowledge_topics`, `open_insights`
- `full_report` / `mentor_blob_v2.full_report_v1`
- `priority_action`, `starters`, `four_week`, `resources`

## Report document (render-time)

| Field | Source |
|---|---|
| `title` | "Spiritual Gifts Report" / "Mentor Report" / template name |
| `subject_name` | apprentice name, else "Apprentice" |
| `date_label` | assessment date as `"%B %-d, %Y"`. If missing: today, labeled "Generated" |
| `story` | list of flowables from `build_*_story` |
