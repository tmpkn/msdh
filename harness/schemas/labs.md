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

## What belongs in `data/labs/`

Analytes that recur and are worth trending: blood and urine chemistry,
hematology, hormones, antibodies, microbiology results, timed urine
collections, saliva hormones, and the few trendable values from stool
panels (calprotectin, elastase, occult blood, H. pylori).

Large one-off profiles do **not** go here: IgG food sensitivity panels,
stool microbiome PCR panels, urinary neurotransmitter profiles, genetic
panels. They are hundreds of items that will never be trended as analytes
and they drown the lab table. They go to `data/other/` with a CSV sidecar
(see `other.md`). A handful of clinically meaningful values from such a
report may additionally be entered as lab rows, pointing at the same
source.

## Analyte naming

Canonical names are lowercase, words joined by underscores. Conventions:

- specimen prefix when not blood: `urine_`, `saliva_`, `stool_`, `csf_`;
  blood is the default and carries no prefix;
- `_24h` for timed collections, `_random` for spot urine;
- `_cr` for values normalised to creatinine;
- `_pct` for percentages, `_absolute` where a count has a percentage twin;
- `_supine` and `_upright`, `_morning`, `_noon`, `_evening`, `_night` for
  posture- or time-specific draws;
- antibodies as `<target>_antibody` or `<target>_igg`, `_igm`, `_iga`.

## `harness/schemas/analytes.csv` and `data/analytes_local.csv`

Canonical analyte names with aliases, so that trends can be followed across
laboratories that name things differently.

```
analyte,aliases,category
```

`aliases` is `|`-separated. Matching is case-insensitive on both the canonical
name and the aliases.

The harness list is upstream and grows with releases. A record may extend
it with `data/analytes_local.csv`, same columns, for names coined during
ingest that the harness does not know yet. Add the row in the same commit
as the lab file that introduces the name. The validator honours both files
and warns once per name that is in neither. When a later harness release
adopts a local name under a different spelling, the migration notes say so.
