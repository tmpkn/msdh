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

## CSV sidecar

A report whose substance is a long list of items (IgG food panel, stool
microbiome PCR, urinary neurotransmitter profile, genetic variant list,
device export) keeps its items in a CSV with the same stem as the markdown:
`2021-07-02_everlywell_food_igg.csv` beside `2021-07-02_everlywell_food_igg.md`.

```
date,item,value,unit,ref_low,ref_high,flag,source,notes
```

`item` is the report's own name for the row, lowercased. The markdown's
*Structured values* section then lists only the handful of items worth a
reader's attention, and *Findings* says what the report concluded. A few
trendable values from such a report may also be entered as lab rows under
canonical analyte names, pointing at the same source.
