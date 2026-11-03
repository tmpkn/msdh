# Procedure: ingest

Brings one external document into the record: a lab report, a clinician's
letter, a discharge summary, an imaging report, a questionnaire, a device
export. Precondition: session-start completed, record onboarded.

One document is one ingest is one commit. A batch of documents is a sequence
of ingests, each committed, with a single summary-refresh at the end of the
batch.

## 1. Receive the document

- **A file outside the repository.** Copy it, never move it, to
  `source/YYYY-MM-DD_slug.ext`. The date is the document's own date: sample
  collection date for labs, visit date for letters, study date for imaging.
  Find it in the document; if it is not there, ask the patient. Keep the
  original extension. Slug is short and descriptive: `quest_cbc`,
  `cardiology_smith_letter`, `mri_lumbar`.
- **Pasted text.** Save it verbatim to `source/YYYY-MM-DD_slug.txt`. Do not
  tidy it.
- **A file already in `source/`.** Use it in place.
- **A photo or scan you cannot read.** Say so. Ask the patient to paste or
  dictate the values. Save what they give you as a `.txt` beside the image
  and treat the text as the source, noting in transcription notes that the
  image was transcribed by the patient.

`source/` files are never modified after this step.

## 2. Read it in full

Read every page. Lab reports often have several pages and a comments
section at the end. Letters have the plan at the bottom. Do not transcribe
from the first page alone.

If a value is illegible or ambiguous, do not guess. Leave it out and record
the gap under transcription notes.

## 3. Classify

- A table of analytes with values and reference ranges is a **lab panel**:
  `data/labs/`, schema `harness/schemas/labs.md`.
- A clinician's account of an encounter is a **visit**: `data/visits/`,
  schema `harness/schemas/visit.md`.
- Anything else is **other**: `data/other/`, schema
  `harness/schemas/other.md`, with the right `subtype`.

One document can yield more than one processed file. A discharge summary
with embedded blood results produces a visit file and a lab file, both
pointing at the same source. That is still one ingest and one commit.

## 4. Transcribe

Read the schema file before writing. Dates, your identity and the harness
version go in the frontmatter as session-start established them.

**Labs.** One row per analyte. Canonical names from
`harness/schemas/analytes.csv`; look up aliases, do not invent spellings. If
an analyte is not in the list, use a clear lowercase name and say so under
transcription notes. Values exactly as printed, units exactly as printed,
no conversions, flags as printed. Write the sibling `.md` with the lab name,
ordering clinician if shown, and every comment the report carries. Then:

```
python3 harness/scripts/msdh.py labs rebuild
```

**Visits.** The clinician must be in `profile/specialists.csv`; add a row if
they are new, and update `last_visit` either way. Then propagate what the
letter says:

- medications started, stopped or changed go into
  `profile/medications.csv` (new row for a new dose, `end` date on the old
  one, `source` = the visit file path);
- a diagnosis the clinician states is voiced in `diags/`: append a `human`
  assessment to the matching file, or open a new file. The clinician's
  words, quoted. If they state it as established, the status may become
  `confirmed`, with `status_by` = the clinician;
- a hypothesis they rule out gets a `human` assessment and, if that was the
  only open question in the file, status `ruled_out`;
- tests ordered and referrals made are listed under *Plan* and will appear
  in the summary's pending section.

**Other.** Transcribe findings faithfully, impression verbatim. Pull any
trackable numbers into *Structured values*.

## 5. Cross-check against the record

This is where the harness earns its keep. Before you write *Harness notes*:

- For every flagged lab value, run `msdh.py labs trend <analyte>`. A single
  low value and a three-year decline are different findings.
- Check the letter against the record: does it mention a medication the
  record says was stopped? Does it omit a condition another specialist is
  treating? Did the clinician have the latest results from elsewhere?
- Check the new findings against every open hypothesis in `diags/`. If
  something bears on one, append a `model` assessment to that file saying
  what and how it moves your confidence.
- Look for the cross-field connection: a cardiology letter plus the thyroid
  panel plus the symptom log. Note it, with the evidence, as inference.

Write these under *Harness notes* (visit, other) or *Transcription notes*
and `diags/` assessments (labs). Keep observation and inference separate.

## 6. Tell the patient

Plainly, in this order: anything urgent; values outside range with the
trend; what the clinician concluded and planned; what you noticed that the
clinician may not have, and which doctor should hear it. Two paragraphs,
not a report.

## 7. Commit

Follow `harness/procedures/commit.md` with `--procedure ingest`. The commit
includes the source file, every processed file, `data/labs_all.csv` if
labs changed, and any `profile/` or `diags/` files you touched. Subject:
`<lab> <panel> <date>` or `<specialty> letter from <clinician> <date>` or
`<subtype> <what> <date>`.

Then `harness/procedures/summary-refresh.md`, or, in a batch, after the
last document.
