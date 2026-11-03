# ClinVar matching tool

Matches a whole-genome VCF against ClinVar and writes dated outputs into
the record's `source/` directory for the genetics procedure to ingest. It
runs by hand, outside the agent, and needs only Python 3.10 or newer. No
packages to install.

## One-time setup

Sequencing files are far too large for the record. Keep them wherever they
are and point a symlink at that place from the record root:

```
ln -s /path/to/your/sequencing/files dna
```

`dna/` is gitignored. The ClinVar download, roughly 100 MB, is cached in
`dna/clinvar/`. Set your genetic findings policy with the agent before the
first run (see `harness/schemas/genetics.md`); if it excludes genes, put
them one per line in a file and pass `--exclude-genes`.

## Run

From the record root:

```
python3 harness/tools/clinvar/analyze_wgs.py --vcf dna/your_genome.vcf.gz
```

First run downloads the current ClinVar release and verifies its checksum.
Later runs reuse the cached copy and print its age; add `--refresh` to
download the current release, which is the point of a periodic check.

Outputs, named by the ClinVar release date:

```
source/YYYY-MM-DD_clinvar_matches.csv
source/YYYY-MM-DD_clinvar_run.json
source/YYYY-MM-DD_clinvar_changes.csv     (when a previous run exists)
```

Then open the agent and say "ingest the ClinVar run".

## Options

| Option | Effect |
|---|---|
| `--refresh` | Download the current ClinVar release instead of using the cache |
| `--clinvar FILE` | Use a specific ClinVar VCF |
| `--build GRCh37\|GRCh38` | Override build detection (normally read from contig lengths) |
| `--include-filtered` | Keep calls whose FILTER is not PASS (default: PASS only) |
| `--min-qual N` | Drop calls below QUAL N |
| `--include-benign` | Keep benign and likely benign matches (default: dropped; they are noise) |
| `--genes FILE` | Report only these genes |
| `--exclude-genes FILE` | Never report these genes |
| `--previous FILE` | Diff against this matches CSV (default: newest older one in the output directory) |
| `--force` | Overwrite outputs for the same release |

## What it does and does not do

- Matches on chromosome, position and both alleles after normalising
  indel representation. Position-only matching is wrong and is not done.
- Reports only alleles the patient actually carries. Homozygous-reference
  sites, missing genotypes and uncarried alternates at multi-allelic sites
  are skipped.
- Classifies ClinVar's significance by token, so a conflicting entry is
  never mistaken for a pathogenic one, and carries the review star level.
- Records the ClinVar release, both checksums and every filter, so a run
  can be reproduced and a later run can be diffed against it.
- Does not know inheritance mode, population frequency or the patient's
  phenotype. That interpretation is the agent's job inside the record, and
  the geneticist's outside it.

It is a screening tool. Nothing it reports is a diagnosis.
