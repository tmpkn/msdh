# Schema: labs

Laboratory results. One CSV per source document, plus a sibling markdown file
with provenance, plus one derived master table.

## `data/labs/YYYY-MM-DD_slug.csv`

One row per analyte on the report. Date is the sample collection date (fall
back to report date if collection date is absent; say so in the sibling notes).

```
date,analyte,value,unit,ref_low,ref_high,flag,lab,source,notes
```

| Column | Values |
|---|---|
| `date` | Collection date, same for every row in the file, equals the filename date |
| `analyte` | Canonical name from `harness/schemas/analytes.csv`. If absent there, use a lowercase descriptive name and note it in the sibling file |
| `value` | Number as printed, decimal point, no units. Non-numeric results (`negative`, `>90`, `<0.1`) are allowed as text |
| `unit` | As printed, e.g. `g/dL`, `mmol/L`, `%`. Empty for unitless |
| `ref_low` | Lower reference bound as printed, empty if none |
| `ref_high` | Upper reference bound as printed, empty if none |
| `flag` | `H`, `L`, `A` (abnormal, non-numeric), or empty. Copy the lab's flag; do not compute one |
| `lab` | Laboratory name, e.g. `quest`, `labcorp`, `nhs_royal_free` |
| `source` | Repo path of the raw document in `source/` |
| `notes` | Free text for that row only |

Do not convert units. Record what the report says. Unit harmonisation is a
query-time concern.

## `data/labs/YYYY-MM-DD_slug.md` (sibling)

Required for every lab CSV. Frontmatter: common keys with `type: lab`,
`date` equal to the CSV's date, `author_kind: model` (the transcriber),
`source` = the raw document path. Additional keys:

| Key | Required | Meaning |
|---|---|---|
| `lab` | yes | Same as the CSV `lab` column |
| `ordered_by` | no | Clinician who ordered the panel |
| `panel` | no | Panel name as printed, e.g. `CBC with differential` |

Body:

```
## Report notes
Anything on the report that is not a row: lab comments, fasting state,
specimen remarks, interpretive text.

## Transcription notes
Anything uncertain: illegible values, analytes not in the canonical list,
assumptions made (e.g. collection date taken from report date).
```

## `data/labs_all.csv` (derived)

Built by `msdh.py labs rebuild` from every per-source CSV. Never edited by
hand. Committed, so that an agent without script access can still read it.

```
date,analyte,value,unit,ref_low,ref_high,flag,lab,source,file,notes
```

Same columns as the per-source files plus `file`, the per-source CSV path.
Sorted by `analyte`, then `date`.

## `harness/schemas/analytes.csv`

Canonical analyte names with aliases, so that trends can be followed across
laboratories that name things differently.

```
analyte,aliases,category
```

`aliases` is `|`-separated. Matching is case-insensitive on both the canonical
name and the aliases. The validator warns, but does not fail, on an analyte
that is not in this list. Additions to the list are made upstream in the
harness; if an analyte is missing, use a clear lowercase name and note it.
