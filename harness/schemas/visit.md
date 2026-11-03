# Schema: visit

`data/visits/YYYY-MM-DD_slug.md`. A processed record of one visit to a human
clinician, derived from a letter, a discharge summary, a portal note, or the
patient's own account of what was said. One file per visit.

Frontmatter: common keys with `type: visit`, `date` = visit date,
`author_kind: model` when transcribed from a document, `author_kind: patient`
when reconstructed from the patient's recollection with no document,
`source` = document path(s) or `none`. Additional keys:

| Key | Required | Meaning |
|---|---|---|
| `clinician` | yes | Name as in `profile/specialists.csv` |
| `clinician_role` | yes | Specialty, lowercase |
| `institution` | no | Where |
| `visit_kind` | yes | `consultation`, `follow_up`, `procedure`, `emergency`, `telehealth`, `other` |

Body sections, in this order. Omit a section only if the source has nothing
for it, and say so with "Not recorded".

```
## Reason for visit

## Clinician's findings
What was examined, measured or observed. Facts from the source, not
interpretation.

## Clinician's assessment
The clinician's stated conclusions and diagnoses, in their words where
possible. If a diagnosis is stated, it must also be voiced in a `diags/`
file with human provenance pointing to this visit.

## Plan
Medications started, stopped or changed (also reflected in
`profile/medications.csv`), tests ordered, referrals, follow-up date.

## Patient's account
Anything the patient reports about the visit that is not in the document:
what was said but not written, how they felt about it, questions they did not
get to ask.

## Harness notes
Observations by the transcribing agent: contradictions with the rest of the
record, things the clinician may not have known, follow-ups the harness
recommends. Clearly inference, not fact.
```
