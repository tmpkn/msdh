# Harness changelog

Patient records carry the harness version in every file they write
(`harness:` in frontmatter, `Harness:` in commit bodies). Entries here say
what changed and whether a record written under an older version needs
migrating.

## 1.1.1 — 2026-11-03

From the first real harness-update and migration. No migration needed.

- harness-update procedure uses three-dot diffs (two-dot listed every
  record file as a deletion) and puts model and runtime in the merge
  commit message.
- Validator warns when a human assessment's author is not a name in
  `profile/specialists.csv`, so one clinician is not spelled three ways
  across a diag file.

## 1.1.0 — 2026-11-03

Lessons from the first real onboarding (one patient, 58 documents, 63
commits in one session).

Changed:

- **Diagnosis assessment order is a warning, not an error.** The 1.0.0
  rule forced an agent to re-date January clinician conclusions as November
  to pass validation. Assessment dates are the date the opinion was formed;
  see `schemas/diag.md`.
- **Record-local analyte list** `data/analytes_local.csv`, honoured by the
  validator and by `labs trend`. Unknown-analyte warnings are now one per
  name, not one per row.
- **Upstream analyte list** grew from 117 to about 240 names, including
  timed urine, saliva, plasma catecholamine, stool and infectious serology
  conventions. Naming conventions documented in `schemas/labs.md`.
- **Large one-off profiles** (IgG food panels, stool PCR, neurotransmitter
  profiles) belong in `data/other/` with a CSV sidecar, not in `data/labs/`.
  Sidecar columns defined in `schemas/other.md` and validated.
- **`specialists.csv` role** must be a plain lowercase specialty; qualifiers
  go in notes. Validated as an error. Visit `clinician` and diag `status_by`
  are cross-checked against the care team (warning).
- **Medications stopped on an unknown date** take an approximate end date
  rather than an empty one.
- `msdh.py symptoms` hides names not reported in the last year unless
  `--all`; shows report counts and age.
- New `msdh.py dedupe <files|dirs>` for checksum comparison against
  `source/` before a batch ingest; ingest procedure covers archives, PDF
  reading, and the local analyte list.
- Onboarding allows closing after round 9 when the patient wants to start
  committing or bringing documents.
- `AGENTS.md` tells agents what to re-read after a context reset.

Migration from 1.0.0 (commit as `--procedure migration`):

1. Required: in `profile/specialists.csv`, make every `role` a plain
   lowercase specialty and move qualifiers to `notes`. Validation fails
   until this is done.
2. Recommended: restore true dates on human assessments in `diags/` that
   were re-dated to the transcription date under 1.0.0; move them into date
   order. Say so in the migration commit subject.
3. Recommended: create `data/analytes_local.csv` listing every analyte name
   the validator still warns about, or rename to the upstream canonical
   name where 1.1.0 now has one (`msdh.py validate` shows the remaining
   names; `labs rebuild` after any rename).
4. Recommended: move IgG food, stool PCR and neurotransmitter profiles from
   `data/labs/` to `data/other/` with a CSV sidecar, keeping only trendable
   values as lab rows; `git mv` the files, then `labs rebuild`.

## 1.0.0 — 2026-11-03

Initial release.

- `AGENTS.md` entry point, `CLAUDE.md` pointer, `harness/PRINCIPLES.md`.
- Schemas for profile, summary, labs, visits, other inputs, symptoms,
  diagnoses and chats; canonical analyte list.
- Procedures: session-start, onboarding, commit (with corrections),
  summary-refresh, ingest, visit, adhoc, second-opinion, harness-update.
- `harness/scripts/msdh.py`: session, status, check-remote, validate,
  commit, tag, labs rebuild/list/trend, symptoms, blind-pack.
