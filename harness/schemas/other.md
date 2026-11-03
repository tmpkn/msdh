# Schema: other

`data/other/YYYY-MM-DD_slug.md`. Processed inputs that are neither a lab
panel nor a clinician visit: imaging reports, pathology, questionnaires,
device exports summaries, genetic reports, prior records obtained from
elsewhere.

Frontmatter: common keys with `type: other`, `date` = date of the study or
document, `source` = raw document path. Additional keys:

| Key | Required | Meaning |
|---|---|---|
| `subtype` | yes | `imaging`, `pathology`, `genetics`, `questionnaire`, `device`, `procedure_report`, `prior_record`, `correspondence`, `misc` |
| `ordered_by` | no | Clinician name |
| `performed_at` | no | Institution |

Body:

```
## Summary
Two to five lines: what was done and the headline result.

## Findings
The report's findings, transcribed faithfully. For imaging, the formal
impression verbatim.

## Structured values
Optional. A markdown table of any numeric values worth tracking (ejection
fraction, bone density T-score, nodule size). Columns: measure, value, unit,
reference.

## Transcription notes
Uncertainties and assumptions.

## Harness notes
Inference and cross-references, clearly labelled as such.
```

If a device export is large tabular data (continuous glucose, blood pressure
log), store the raw export in `source/` and a processed CSV next to this
file with the same stem; the markdown describes the columns.
