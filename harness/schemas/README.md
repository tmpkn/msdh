# Schemas

Every file in the record has a schema here. `msdh.py validate` enforces them.
A file that does not validate must not be committed.

## File naming

- Dated files: `YYYY-MM-DD_short_slug.ext`. The date is the date of the event
  the file describes (visit date, sample collection date, journal date), not
  the date it was written. Slug is lowercase ASCII, digits and underscores.
- Fixed files have fixed names: `SUMMARY.md`, `profile/profile.md`,
  `profile/medications.csv`, `profile/specialists.csv`, `symptoms/log.csv`,
  `data/labs_all.csv`.
- `source/` files keep a date prefix and a descriptive slug but any extension:
  `source/2026-11-02_quest_cbc.pdf`. Original filenames can be kept after the
  slug if useful. Contents are never modified.

## Common frontmatter

Every markdown file in the record starts with YAML-style frontmatter. Keys are
flat (no nesting), one per line, `key: value`. Values are plain strings; do
not quote them unless they contain a colon.

```
---
type: visit
title: Cardiology follow-up with Dr Smith
date: 2026-10-15
created: 2026-11-03
harness: 1.0.0
author_kind: model
author: claude-fable-5-1
author_runtime: claude-code 2.1.0
source: source/2026-10-15_cardiology_letter.pdf
---
```

| Key | Required | Meaning |
|---|---|---|
| `type` | yes | One of `profile`, `summary`, `lab`, `visit`, `other`, `symptom`, `diag`, `chat` |
| `title` | yes | Short human title |
| `date` | yes | Event date, `YYYY-MM-DD`. Must equal the filename date for dated files |
| `created` | yes | Date the file was written, `YYYY-MM-DD` |
| `harness` | yes | MSDH harness version that wrote the file, from `harness/VERSION` |
| `author_kind` | yes | `model`, `human` or `patient`. Who produced the *content of this file* |
| `author` | yes | Model ID (`claude-fable-5-1`), person's name, or `patient` |
| `author_runtime` | if model | Agent runtime and version, e.g. `claude-code 2.1.0`, `codex 0.9`, `pi 1.4` |
| `source` | yes | Comma-separated repo-relative paths this file was derived from, or `none` |

`author` is the writer of the file. When a model transcribes a doctor's
letter into a visit note, the author is the model and the doctor is recorded in
type-specific fields (`clinician`, `clinician_role`). The doctor's own
conclusions are voiced directly, with human provenance, in `diags/` assessments.

Type-specific keys are listed in each schema file. Unknown keys are allowed
but ignored by the validator; prefer not to invent them.

## CSV conventions

- UTF-8, comma-separated, header row exactly as the schema lists it, in that
  order. No extra columns.
- Dates `YYYY-MM-DD`. Empty cell means unknown, never `N/A` or `-`.
- Numbers use `.` as decimal separator and no thousands separators.
- Free text goes in a `notes` column; everything else is a controlled value.

## Provenance for CSV files

CSV files cannot carry frontmatter. Each per-source lab CSV therefore has a
sibling markdown file with the same stem (`2026-11-02_quest_cbc.csv` and
`2026-11-02_quest_cbc.md`) carrying the provenance and any narrative from the
report. The fixed CSVs (`log.csv`, `medications.csv`, `specialists.csv`) get
their provenance from the commit that changed them, which is why commits are
one operation each.

## Schema files

| File | Covers |
|---|---|
| `profile.md` | `profile/profile.md`, `profile/medications.csv`, `profile/specialists.csv` |
| `summary.md` | `SUMMARY.md` |
| `labs.md` | `data/labs/*.csv`, their `.md` siblings, `data/labs_all.csv`, `analytes.csv` |
| `visit.md` | `data/visits/*.md` |
| `other.md` | `data/other/*.md` |
| `symptoms.md` | `symptoms/*.md`, `symptoms/log.csv` |
| `diag.md` | `diags/*.md` |
| `chat.md` | `chats/*.md` |
