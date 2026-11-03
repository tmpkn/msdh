# Schema: diag

`diags/YYYY-MM-DD_slug.md`. One file per hypothesis, diagnosis or significant
unexplained finding. The file is multi-voiced: it collects dated assessments
from human clinicians and from models, each with its own provenance, in
chronological order. Files are never deleted. A hypothesis that is dropped is
marked `ruled_out` or `superseded` with a reason.

The filename date is the date the entry was opened. `date` in frontmatter
equals it.

Frontmatter: common keys with `type: diag`, `author` = who opened the file.
Additional keys:

| Key | Required | Meaning |
|---|---|---|
| `status` | yes | `hypothesis`, `under_investigation`, `confirmed`, `ruled_out`, `superseded` |
| `status_date` | yes | Date the status was last changed |
| `status_by` | yes | Who set the current status: model ID or clinician name |
| `superseded_by` | if superseded | Path of the `diags/` file that replaces this one |
| `fields` | yes | Comma-separated specialties this touches: `cardiology, endocrinology` |

Status meaning:

- `hypothesis`: proposed, not yet taken to a clinician.
- `under_investigation`: a clinician is aware and tests or referrals are in
  progress.
- `confirmed`: a clinician has made the diagnosis. Only a human can confirm.
  The confirming assessment must be voiced with human provenance.
- `ruled_out`: excluded by a clinician or by test results. Reason required in
  the closing assessment.
- `superseded`: replaced by a better-framed entry.

Body:

```
## Summary
Current state in two to five lines. Rewritten when status changes.

## Evidence
- Supporting: bullet list, each linking a record file (lab row, visit, symptom)
- Against: same

## What would settle it
Tests, findings or time that would confirm or exclude. Concrete.

## Assessments
### YYYY-MM-DD | model | claude-fable-5-1 | claude-code 2.1.0
Free text. The reasoning, the confidence, the recommended next step.

### YYYY-MM-DD | human | Dr Jane Smith (cardiologist) | data/visits/2026-10-15_cardiology_smith.md
The clinician's view, as stated in the linked source. Quote where possible.

### YYYY-MM-DD | patient | patient | chats/2026-11-03_consultation.md
The patient's own view, when it matters.
```

Assessment header format is strict, four fields separated by ` | `:

1. date `YYYY-MM-DD`
2. kind: `model`, `human`, `patient`
3. author: model ID, or clinician name with role in parentheses, or `patient`
4. for a model: the runtime; for human or patient: the repo path of the source

The assessment date is the date the opinion was formed: for a model, the
session date; for a human, the date of the document or visit in which they
stated it, not the date it was transcribed into the record. A clinician's
conclusion from a January letter ingested in November is dated January.

Keep assessments in date order where practical, which means inserting an
older human assessment above newer model ones when a historical document is
ingested. The validator warns, and does not fail, on out-of-order entries;
never falsify a date to satisfy ordering. The text of an assessment is never
edited after the fact. A changed mind is a new assessment.

## Second opinions

A second-opinion assessment is one written by a model that has read the
record but not the existing `## Assessments` section of this file. The
procedure handles the blinding; the schema only requires that such an
assessment start its text with `Blind assessment.` so that readers know.
