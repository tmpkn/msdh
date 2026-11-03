# Schema: summary

`SUMMARY.md` at the repository root. The physician's working memory: what a
good generalist would want in front of them before answering any question
about this patient. Roughly one page. Rewritten, not appended, after every
change to the record, by the summary-refresh procedure.

Frontmatter: common keys with `type: summary`, `date` = date of this
rewrite, `author_kind: model`, `source: none`. Additional key:

| Key | Meaning |
|---|---|
| `record_commit` | Short hash of the commit the summary was built from |

Body sections, all present, in this order:

```
## Patient
One line: age, sex, the two or three defining facts.

## Problem list
Active conditions and significant unexplained findings, one bullet each,
most important first. Each bullet: the problem, since when, who manages it,
current status. Link to the `diags/` file where one exists.

## Active medications
From `profile/medications.csv` rows with no end date. Name, dose, frequency,
reason. One bullet each.

## Allergies
One line, or "None reported".

## Open hypotheses
From `diags/` files with status `hypothesis` or `under_investigation`. One
bullet each: the hypothesis, the evidence for and against in a clause each,
what would settle it. Link to the file.

## Pending and recommended
Tests ordered but not yet resulted, referrals outstanding, and the harness's
own recommendations not yet acted on. Each with who should do it.

## Recent changes
The last ten or so notable events in reverse chronological order: new
results, visits, symptom changes, medication changes. Date and one line each.

## Watch list
Trends worth tracking even if not yet a problem. Analyte or symptom, direction,
and the span of time over which it has moved.
```

Rules:

- Everything here must be traceable to a file in the record. No fact appears
  in the summary that is not in the record.
- Brevity is the point. If it grows past about 120 lines, prune the recent
  changes and watch list first.
- Urgent findings are not buried here. They are raised with the patient in
  the session that found them.
