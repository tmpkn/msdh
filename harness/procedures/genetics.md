# Procedure: genetics

Brings one ClinVar run into the record. The run itself happens outside the
agent: the patient executes `harness/tools/clinvar/analyze_wgs.py` by hand
against their sequencing file, and it writes three dated files into
`source/`. This procedure ingests them. Precondition: session-start
completed, record onboarded.

Read `harness/schemas/genetics.md` first. Everything in it about screening
versus diagnosis applies to how you talk to the patient as much as to what
you write.

## 1. Policy first

Check `profile/profile.md` for a `## Genetic findings policy` section. If
it is missing, stop before reading any match and set it with the patient:
whether they want everything, only certain genes, or everything except
certain genes or conditions; and whether they want ACMG secondary findings
reported at all. Explain in two sentences what secondary findings are: well
supported, medically actionable variants unrelated to why the genome was
sequenced. Record the policy in the profile with a changelog line, commit
it as a `correction`, and only then continue.

If the policy excludes genes, confirm the run metadata (`_run.json`,
`filters`) shows the exclusion was applied. If it was not, do not ingest;
tell the patient to re-run with `--exclude-genes`.

## 2. Find the run

```
ls source/*_clinvar_*
```

The newest release date not yet represented in `data/genetics/` is the one
to ingest. The three files share the date. If `_run.json` is missing, the
run is incomplete; ask the patient to re-run.

Read `_run.json` in full. Check that `vcf.sha256` matches the previous
report's `vcf_sha256` if there is one; a different genome is a different
patient, or a re-sequencing, and either needs the patient's confirmation.

## 3. Read the matches

Read `_changes.csv` first if it exists; that is what is new. Then the
matches CSV, tier by tier. For a first run that is a long list; the
`uncertain` tier can be thousands of rows and is not read line by line.
Read `pathogenic`, `conflicting`, `risk` and `drug_response` in full, and
search `uncertain` for genes that connect to this patient (step 4).

For each pathogenic or likely pathogenic match with two or more stars,
work out what the zygosity means for the condition named. ClinVar does not
carry inheritance mode; use your knowledge, state it as such, and say when
you are unsure. A heterozygous match for a recessive condition is carrier
status and is not a finding about the patient's health, though it may
matter for family planning.

## 4. Connect to the record

This is the point of running it inside MSDH. With `SUMMARY.md`, the open
`diags/`, the symptom log and the family history in mind, search every tier
including `uncertain` for genes plausibly related to the patient's actual
problems. State each connection with the evidence on both sides and a
confidence in words. A variant of uncertain significance in a gene for a
condition the patient has symptoms of is a question for a geneticist; it is
not an explanation.

Anything that looks urgent, meaning a well supported dominant pathogenic
finding with an actionable condition, is said to the patient now, plainly,
with the advice to seek genetic counselling.

## 5. Write the record

1. Copy the matches CSV to `data/genetics/variants.csv`, replacing the
   previous one.
2. Write `data/genetics/YYYY-MM-DD_clinvar_<release>.md` per the schema,
   with `previous_report` set when there was one.
3. For a pathogenic match at two or more stars that is relevant to the
   patient's health (not a carrier state), and for any match you flagged
   under *Relevant to this patient* with more than low confidence, open or
   update a `diags/` entry with `status: hypothesis`, fields including
   `genetics`, and an assessment that says what confirmatory testing would
   settle it. One entry per gene or condition, not per variant.
4. For a refresh, a reclassification to or from pathogenic gets its own
   assessment in the affected `diags/` entry, or a new entry.
5. `profile/profile.md`: nothing, unless the patient asked for the policy
   to change.

## 6. Tell the patient

In this order: anything urgent; what changed since the last run, if any;
pathogenic matches with strong support and what they mean given zygosity;
connections to their existing picture; what to take to which clinician.
Then the standing caveat, once, in one sentence: these are screening
matches from a research database, and anything that matters is confirmed
by a clinical test before it is acted on.

## 7. Commit

Follow `harness/procedures/commit.md` with `--procedure genetics` and the
subject `ClinVar <release> run` or `ClinVar <release> refresh: <headline
change>`. The commit includes the three source files, `variants.csv`, the
report, and any `diags/` files. Then `harness/procedures/summary-refresh.md`.
Genetic findings go on the summary's problem list only when a clinician
has confirmed them; until then they appear under open hypotheses.
