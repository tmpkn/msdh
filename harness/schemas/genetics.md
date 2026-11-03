# Schema: genetics

Results of matching the patient's sequencing data against ClinVar, produced
by `harness/tools/clinvar/analyze_wgs.py` outside the agent and brought in
by the genetics procedure. Everything here is **screening**: a match is a
reason to ask a clinical geneticist, never a diagnosis. Most pathogenic
matches are recessive carrier states or weakly supported entries.

The sequencing data itself never enters the record. It lives behind
`dna/`, a gitignored symlink to wherever the files physically are.

## `source/YYYY-MM-DD_clinvar_matches.csv`, `_run.json`, `_changes.csv`

The tool's raw outputs, dated by the ClinVar release they were computed
against. Immutable like everything in `source/`. The matches CSV columns:

```
chrom,pos,ref,alt,gene,rsid,zygosity,filter,qual,tier,clinsig,low_penetrance,clnsigconf,review_status,stars,conditions,variation_id,acmg_sf,clinvar_url
```

| Column | Meaning |
|---|---|
| `chrom`, `pos`, `ref`, `alt` | Normalised variant, chromosome without `chr` prefix |
| `gene` | Gene symbol from ClinVar |
| `rsid` | dbSNP id when ClinVar carries one |
| `zygosity` | `heterozygous`, `homozygous`, `hemizygous` |
| `filter`, `qual` | From the patient's VCF |
| `tier` | `pathogenic`, `conflicting`, `risk`, `drug_response`, `uncertain`, `other`, `benign`. Benign is omitted by default |
| `clinsig` | ClinVar's classification string, verbatim |
| `low_penetrance` | `yes` when ClinVar qualifies the classification so |
| `clnsigconf` | The conflicting submissions, when the tier is conflicting |
| `review_status`, `stars` | ClinVar review status and its star level, 0 to 4 |
| `conditions` | ClinVar condition names, `|`-separated |
| `variation_id`, `clinvar_url` | ClinVar's identifier and page |
| `acmg_sf` | `yes` when the gene is on the ACMG secondary findings list |

`_run.json` holds the tool version, the VCF checksum and build, the ClinVar
release and checksum, the filters used, and counts. `_changes.csv` lists
new, removed, reclassified and review-changed matches against the previous
run.

## `data/genetics/variants.csv`

The current match table: a verbatim copy of the most recently ingested
matches CSV. Replaced wholesale by each genetics ingest, so that the record
always holds one answer to "what does ClinVar say about this genome today".
History lives in `source/` and in git.

## `data/genetics/YYYY-MM-DD_clinvar_<release>.md`

One report per ingested run. Filename date equals the ClinVar release date.
Frontmatter: common keys with `type: genetics`, `date` = release date,
`author_kind: model`, `source` = the three source files. Additional keys:

| Key | Required | Meaning |
|---|---|---|
| `clinvar_release` | yes | `YYYY-MM-DD` from the run metadata |
| `build` | yes | `GRCh37` or `GRCh38` |
| `vcf_sha256` | yes | From the run metadata, so the genome the run used is identifiable |
| `tool_version` | yes | From the run metadata |
| `previous_report` | no | Path of the previous `data/genetics/` report, if any |

Body sections, in this order:

```
## Summary
Counts by tier, number of pathogenic matches at two or more stars, number of
ACMG secondary-findings genes hit, and whether this is the first run or a
refresh.

## Changes since previous run
From `_changes.csv`. Reclassifications first, then new, then removed. "First
run" when there is no previous. A reclassification to or from pathogenic is
the headline of this section.

## Pathogenic and likely pathogenic
One bullet per match with two or more stars: gene, variant, zygosity, the
condition, and what zygosity means for it (carrier of a recessive condition,
or a dominant finding). Then one line summarising the weaker ones by count.
Matches in genes on the patient's exclusion policy are not listed.

## Relevant to this patient
The cross-field section. Matches, at any tier including uncertain, in genes
plausibly connected to the patient's existing problems, symptoms or family
history, with the connection stated and the confidence given in words. This
is where the harness adds something a generic report cannot.

## Transcription notes
Filters used, anything odd in the run metadata.

## Harness notes
Recommendations: which matches deserve confirmatory testing or a genetics
referral, and for which clinician. Inference, labelled.
```

## Genetic findings policy

Before the first genetics ingest, `profile/profile.md` must carry a
section:

```
## Genetic findings policy
- Scope: <everything | listed genes only | everything except listed genes>
- Excluded genes or conditions: <list, or none>
- Secondary findings: <report | do not report>
- Set on: YYYY-MM-DD
```

The policy is the patient's and is recorded before any match is read. The
tool's `--genes` and `--exclude-genes` options implement it at run time;
the procedure checks the run metadata against the policy.
