#!/usr/bin/env python3
"""analyze_wgs.py: match a whole-genome VCF against ClinVar. MSDH tool.

Runs outside the agent, by hand, on the patient's machine. Standard library
only. Produces dated files for the record's `source/` directory which the
genetics procedure then ingests.

  python3 harness/tools/clinvar/analyze_wgs.py --vcf dna/genome.vcf.gz

Outputs, named by the ClinVar release date, into --out-dir (default source/):

  YYYY-MM-DD_clinvar_matches.csv   every carried variant with a ClinVar entry
  YYYY-MM-DD_clinvar_run.json      run metadata: build, checksums, release, filters, counts
  YYYY-MM-DD_clinvar_changes.csv   differences from the previous run, when one exists

This is a screening tool. A match is a reason to ask a clinical geneticist,
never a diagnosis.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

VERSION = "2.0.1"
CLINVAR_BASE = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_{build}/clinvar.vcf.gz"
BUILD_CONTIG_LENGTHS = {
    "GRCh38": {"1": 248956422, "2": 242193529, "X": 156040895},
    "GRCh37": {"1": 249250621, "2": 243199373, "X": 155270560},
}
SYMBOLIC = ("<NON_REF>", "<*>", ".", "*")
COLUMNS = ["chrom", "pos", "ref", "alt", "gene", "rsid", "zygosity", "filter", "qual",
           "tier", "clinsig", "low_penetrance", "clnsigconf", "review_status", "stars",
           "conditions", "variation_id", "acmg_sf", "clinvar_url"]
TIER_ORDER = ["pathogenic", "conflicting", "risk", "drug_response", "uncertain", "other", "benign"]
STARS = {
    "practice_guideline": 4,
    "reviewed_by_expert_panel": 3,
    "criteria_provided,_multiple_submitters,_no_conflicts": 2,
    "criteria_provided,_conflicting_classifications": 1,
    "criteria_provided,_conflicting_interpretations": 1,
    "criteria_provided,_single_submitter": 1,
}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def open_text(path: str):
    if str(path).endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, encoding="utf-8", errors="replace")


def file_digest(path: str, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_chrom(c: str) -> str:
    c = c[3:] if c.lower().startswith("chr") else c
    return "MT" if c in ("M", "chrM") else c


def normalize_allele(pos: int, ref: str, alt: str) -> tuple[int, str, str]:
    """Minimal representation for matching: trim the shared suffix, then the
    shared prefix, moving pos to the first differing base. Alleles may become
    empty (a pure insertion or deletion). Left- and right-anchored spellings
    of the same event then produce the same key. Repeat-context left
    alignment needs the reference genome and is not attempted; ClinVar and
    common callers both left-align, so this covers the usual case."""
    while ref and alt and ref[-1] == alt[-1]:
        ref, alt = ref[:-1], alt[:-1]
    while ref and alt and ref[0] == alt[0]:
        ref, alt = ref[1:], alt[1:]
        pos += 1
    return pos, ref, alt


def read_header(path: str) -> tuple[list[str], list[str]]:
    """Header lines and sample names, without reading the body."""
    lines: list[str] = []
    samples: list[str] = []
    with open_text(path) as f:
        for line in f:
            if line.startswith("##"):
                lines.append(line.rstrip("\n"))
            elif line.startswith("#CHROM"):
                samples = line.rstrip("\n").split("\t")[9:]
                break
            else:
                break
    return lines, samples


def detect_build(header: list[str]) -> str | None:
    lengths: dict[str, int] = {}
    for ln in header:
        if ln.startswith("##contig="):
            m_id = re.search(r"ID=([^,>]+)", ln)
            m_len = re.search(r"length=(\d+)", ln)
            if m_id and m_len:
                lengths[norm_chrom(m_id.group(1))] = int(m_len.group(1))
    for build, ref in BUILD_CONTIG_LENGTHS.items():
        if any(lengths.get(c) == n for c, n in ref.items()):
            return build
    text = "\n".join(header).lower()
    if "grch38" in text or "hg38" in text:
        return "GRCh38"
    if "grch37" in text or "hg19" in text:
        return "GRCh37"
    return None


def header_value(header: list[str], key: str) -> str:
    for ln in header:
        if ln.startswith(f"##{key}="):
            return ln.split("=", 1)[1].strip()
    return ""


def read_gene_list(path: str | None) -> set[str]:
    if not path:
        return set()
    out: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for ln in f:
            ln = ln.split("#", 1)[0].strip()
            if ln:
                out.add(ln.upper())
    return out


# --------------------------------------------------------------------------
# patient VCF
# --------------------------------------------------------------------------

def read_patient(path: str, include_filtered: bool, min_qual: float) -> tuple[dict, dict]:
    """One pass. Returns {(chrom,pos,ref,alt): info} for alleles the patient
    carries, plus summary statistics."""
    variants: dict[tuple, dict] = {}
    stats = {"records": 0, "variant_sites": 0, "filtered_out": 0, "low_qual": 0,
             "missing_genotype": 0, "hom_ref_sites": 0,
             "by_type": Counter(), "by_zygosity": Counter(), "by_chrom": Counter()}
    gt_index: int | None = None
    last_format = None
    with open_text(path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            stats["records"] += 1
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 10:
                continue
            chrom, pos_s, _id, ref, alt_s, qual_s, filt, _info, fmt, sample = fields[:10]
            alts = alt_s.split(",")
            if all(a in SYMBOLIC or a.startswith("<") for a in alts):
                continue
            if fmt != last_format:
                keys = fmt.split(":")
                gt_index = keys.index("GT") if "GT" in keys else None
                last_format = fmt
            if gt_index is None:
                stats["missing_genotype"] += 1
                continue
            gt_s = sample.split(":")[gt_index] if gt_index < len(sample.split(":")) else "."
            alleles = [a for a in re.split(r"[/|]", gt_s)]
            if not alleles or any(a in (".", "") for a in alleles):
                stats["missing_genotype"] += 1
                continue
            idxs = [int(a) for a in alleles]
            carried = sorted({i for i in idxs if i > 0})
            if not carried:
                stats["hom_ref_sites"] += 1
                continue
            if not include_filtered and filt not in ("PASS", "."):
                stats["filtered_out"] += 1
                continue
            try:
                qual = float(qual_s) if qual_s != "." else None
            except ValueError:
                qual = None
            if min_qual and qual is not None and qual < min_qual:
                stats["low_qual"] += 1
                continue
            stats["variant_sites"] += 1
            c = norm_chrom(chrom)
            stats["by_chrom"][c] += 1
            for i in carried:
                alt = alts[i - 1]
                if alt in SYMBOLIC or alt.startswith("<"):
                    continue
                n = idxs.count(i)
                if len(idxs) == 1:
                    zyg = "hemizygous"
                elif n == len(idxs):
                    zyg = "homozygous"
                else:
                    zyg = "heterozygous"
                stats["by_zygosity"][zyg] += 1
                if len(ref) == 1 and len(alt) == 1:
                    stats["by_type"]["snv"] += 1
                elif len(ref) > len(alt):
                    stats["by_type"]["deletion"] += 1
                elif len(ref) < len(alt):
                    stats["by_type"]["insertion"] += 1
                else:
                    stats["by_type"]["mnv"] += 1
                p, r, a = normalize_allele(int(pos_s), ref, alt)
                variants[(c, p, r, a)] = {"zygosity": zyg, "filter": filt,
                                          "qual": "" if qual is None else f"{qual:g}",
                                          "pos": int(pos_s), "ref": ref, "alt": alt}
    return variants, stats


# --------------------------------------------------------------------------
# ClinVar
# --------------------------------------------------------------------------

def download(url: str, dest: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": f"msdh-clinvar/{VERSION}"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as out:
        total = r.headers.get("Content-Length")
        done = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                print(f"\r  {done / (1 << 20):7.1f} / {int(total) / (1 << 20):.1f} MB", end="", flush=True)
        print()


def ensure_clinvar(cache_dir: str, build: str, refresh: bool, explicit: str | None) -> str:
    if explicit:
        if not os.path.exists(explicit):
            sys.exit(f"ClinVar file not found: {explicit}")
        return explicit
    os.makedirs(cache_dir, exist_ok=True)
    cached = sorted(glob.glob(os.path.join(cache_dir, f"clinvar_{build}_*.vcf.gz")))
    if cached and not refresh:
        path = cached[-1]
        m = re.search(r"_(\d{4}-\d{2}-\d{2})\.vcf\.gz$", path)
        if m:
            age = (dt.date.today() - dt.date.fromisoformat(m.group(1))).days
            print(f"ClinVar: using cached {os.path.basename(path)} ({age} days old; --refresh to update)")
        return path
    url = CLINVAR_BASE.format(build=build)
    tmp = os.path.join(cache_dir, "clinvar_download.vcf.gz")
    print(f"ClinVar: downloading {url}")
    download(url, tmp)
    try:
        md5_url = url + ".md5"
        with urllib.request.urlopen(md5_url, timeout=60) as r:
            expected = r.read().decode().split()[0].strip()
        actual = file_digest(tmp, "md5")
        if expected != actual:
            os.remove(tmp)
            sys.exit(f"ClinVar download failed its MD5 check ({actual} != {expected}). Try again.")
        print("ClinVar: MD5 verified")
    except urllib.error.URLError:
        print("ClinVar: could not fetch the MD5 file; continuing without verification")
    header, _ = read_header(tmp)
    file_date = header_value(header, "fileDate")
    release = file_date if re.match(r"^\d{4}-\d{2}-\d{2}$", file_date) else dt.date.today().isoformat()
    final = os.path.join(cache_dir, f"clinvar_{build}_{release}.vcf.gz")
    shutil.move(tmp, final)
    print(f"ClinVar: release {release} saved as {final}")
    return final


def parse_info(info: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in info.split(";"):
        if "=" in item:
            k, v = item.split("=", 1)
            out[k] = v
        else:
            out[item] = "1"
    return out


def classify(clnsig: str) -> tuple[str, bool]:
    """Map ClinVar's CLNSIG string to a tier. Token-based: no substring traps."""
    tokens = [t for t in re.split(r"[|/]", clnsig) if t]
    low_pen = any(",_low_penetrance" in t for t in tokens)
    tokens = [t.replace(",_low_penetrance", "") for t in tokens]
    tier = "other"
    found: set[str] = set()
    for t in tokens:
        tl = t.lower()
        if tl in ("pathogenic", "likely_pathogenic"):
            found.add("pathogenic")
        elif tl.startswith("conflicting_"):
            found.add("conflicting")
        elif tl in ("uncertain_significance", "uncertain_risk_allele"):
            found.add("uncertain")
        elif tl == "drug_response":
            found.add("drug_response")
        elif tl in ("risk_factor", "likely_risk_allele", "established_risk_allele",
                    "association", "affects", "protective"):
            found.add("risk")
        elif tl in ("benign", "likely_benign"):
            found.add("benign")
        else:
            found.add("other")
    for t in TIER_ORDER:
        if t in found:
            tier = t
            break
    return tier, low_pen


def stars_for(revstat: str) -> int:
    return STARS.get(revstat, 0)


def stream_clinvar(path: str, patient: dict, acmg: set[str]) -> tuple[list[dict], str]:
    matches: list[dict] = []
    release = ""
    n = 0
    with open_text(path) as f:
        for line in f:
            if line.startswith("#"):
                if line.startswith("##fileDate="):
                    release = line.strip().split("=", 1)[1]
                continue
            n += 1
            if n % 500000 == 0:
                print(f"\r  ClinVar records scanned: {n:,}", end="", flush=True)
            fields = line.rstrip("\n").split("\t", 8)
            if len(fields) < 8:
                continue
            chrom, pos_s, vid, ref, alt_s, _q, _f, info_s = fields[:8]
            c = norm_chrom(chrom)
            for alt in alt_s.split(","):
                if alt in SYMBOLIC or alt.startswith("<"):
                    continue
                key = normalize_allele(int(pos_s), ref, alt)
                key = (c, key[0], key[1], key[2])
                hit = patient.get(key)
                if hit is None:
                    continue
                info = parse_info(info_s)
                clnsig = info.get("CLNSIG", "")
                if not clnsig:
                    continue
                tier, low_pen = classify(clnsig)
                gene = (info.get("GENEINFO", "").split("|")[0].split(":")[0]) if info.get("GENEINFO") else ""
                revstat = info.get("CLNREVSTAT", "")
                matches.append({
                    "chrom": c, "pos": hit["pos"], "ref": hit["ref"], "alt": hit["alt"],
                    "gene": gene,
                    "rsid": ("rs" + info["RS"]) if info.get("RS") else "",
                    "zygosity": hit["zygosity"], "filter": hit["filter"], "qual": hit["qual"],
                    "tier": tier, "clinsig": clnsig, "low_penetrance": "yes" if low_pen else "",
                    "clnsigconf": info.get("CLNSIGCONF", ""),
                    "review_status": revstat, "stars": stars_for(revstat),
                    "conditions": info.get("CLNDN", ""),
                    "variation_id": vid,
                    "acmg_sf": "yes" if gene.upper() in acmg else "",
                    "clinvar_url": f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{vid}/" if vid.isdigit() else "",
                })
    print(f"\r  ClinVar records scanned: {n:,}")
    return matches, release


# --------------------------------------------------------------------------
# outputs
# --------------------------------------------------------------------------

def write_csv(path: str, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in columns})


def read_matches(path: str) -> dict[tuple, dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return {(r["chrom"], int(r["pos"]), r["ref"], r["alt"]): r for r in csv.DictReader(f)}


def diff_runs(prev: dict[tuple, dict], cur: list[dict]) -> list[dict]:
    changes: list[dict] = []
    cur_map = {(r["chrom"], r["pos"], r["ref"], r["alt"]): r for r in cur}
    for key, r in cur_map.items():
        old = prev.get(key)
        base = {"chrom": key[0], "pos": key[1], "ref": key[2], "alt": key[3],
                "gene": r["gene"], "zygosity": r["zygosity"]}
        if old is None:
            changes.append({**base, "change": "new", "old_tier": "", "new_tier": r["tier"],
                            "old_clinsig": "", "new_clinsig": r["clinsig"],
                            "old_stars": "", "new_stars": r["stars"]})
        elif old["tier"] != r["tier"] or old["clinsig"] != r["clinsig"]:
            changes.append({**base, "change": "reclassified", "old_tier": old["tier"], "new_tier": r["tier"],
                            "old_clinsig": old["clinsig"], "new_clinsig": r["clinsig"],
                            "old_stars": old["stars"], "new_stars": r["stars"]})
        elif str(old["stars"]) != str(r["stars"]):
            changes.append({**base, "change": "review_changed", "old_tier": old["tier"], "new_tier": r["tier"],
                            "old_clinsig": old["clinsig"], "new_clinsig": r["clinsig"],
                            "old_stars": old["stars"], "new_stars": r["stars"]})
    for key, old in prev.items():
        if key not in cur_map:
            changes.append({"chrom": key[0], "pos": key[1], "ref": key[2], "alt": key[3],
                            "gene": old.get("gene", ""), "zygosity": old.get("zygosity", ""),
                            "change": "removed", "old_tier": old["tier"], "new_tier": "",
                            "old_clinsig": old["clinsig"], "new_clinsig": "",
                            "old_stars": old["stars"], "new_stars": ""})
    order = {"reclassified": 0, "new": 1, "removed": 2, "review_changed": 3}
    changes.sort(key=lambda c: (order[c["change"]], TIER_ORDER.index(c["new_tier"] or c["old_tier"]), c["chrom"], int(c["pos"])))
    return changes


CHANGE_COLUMNS = ["change", "chrom", "pos", "ref", "alt", "gene", "zygosity",
                  "old_tier", "new_tier", "old_clinsig", "new_clinsig", "old_stars", "new_stars"]


CANONICAL = [str(i) for i in range(1, 23)] + ["X", "Y", "MT"]


def genome_stats(stats: dict) -> dict:
    """Counters as plain dicts; per-chromosome counts limited to the canonical
    contigs so the metadata file stays readable (a GRCh38 VCF has 1,600 contigs)."""
    out: dict = {}
    for k, v in stats.items():
        if k == "by_chrom":
            canon = {c: v[c] for c in CANONICAL if c in v}
            other = {c: n for c, n in v.items() if c not in canon}
            out["by_chrom"] = canon
            out["other_contigs"] = {"contigs": len(other), "variant_sites": sum(other.values())}
        elif isinstance(v, Counter):
            out[k] = dict(v)
        else:
            out[k] = v
    return out


def print_summary(stats: dict, matches: list[dict], changes: list[dict] | None, build: str, release: str) -> None:
    print("\n=== genome ===")
    print(f"build {build}; records {stats['records']:,}; carried variant sites {stats['variant_sites']:,}; "
          f"filtered out {stats['filtered_out']:,}; hom-ref {stats['hom_ref_sites']:,}; "
          f"missing GT {stats['missing_genotype']:,}")
    print("by type: " + ", ".join(f"{k} {v:,}" for k, v in stats["by_type"].most_common()))
    print("by zygosity: " + ", ".join(f"{k} {v:,}" for k, v in stats["by_zygosity"].most_common()))
    print(f"\n=== ClinVar {release} ===")
    tiers = Counter(m["tier"] for m in matches)
    print("matches: " + ", ".join(f"{t} {tiers[t]:,}" for t in TIER_ORDER if tiers[t]))
    strong = [m for m in matches if m["tier"] == "pathogenic" and int(m["stars"]) >= 2]
    weak = [m for m in matches if m["tier"] == "pathogenic" and int(m["stars"]) < 2]
    print(f"pathogenic or likely pathogenic: {len(strong)} with two or more stars, {len(weak)} with fewer")
    for m in sorted(strong, key=lambda m: (-int(m["stars"]), m["gene"])):
        print(f"  {m['gene']:<10} {m['chrom']}:{m['pos']} {m['ref']}>{m['alt']} {m['zygosity']:<12} "
              f"{m['stars']}* {m['clinsig']}  {m['conditions'][:70]}")
    if changes is not None:
        kinds = Counter(c["change"] for c in changes)
        print("\n=== changes since previous run ===")
        print(", ".join(f"{k} {v}" for k, v in kinds.items()) or "none")
        for c in changes:
            if c["change"] in ("reclassified", "new") and (c["new_tier"] in ("pathogenic", "conflicting")):
                print(f"  {c['change']:<13} {c['gene']:<10} {c['chrom']}:{c['pos']} "
                      f"{c['old_clinsig'] or '-'} -> {c['new_clinsig']}")
    print("\nScreening only. Pathogenic matches need confirmatory clinical testing and a "
          "geneticist's interpretation; many are recessive carrier states.")


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vcf", required=True, help="patient VCF (.vcf or .vcf.gz), one sample")
    ap.add_argument("--out-dir", default="source", help="where the dated outputs go (default: source/)")
    ap.add_argument("--clinvar", help="use this ClinVar VCF instead of the cache")
    ap.add_argument("--clinvar-dir", default="dna/clinvar", help="ClinVar cache directory (default: dna/clinvar)")
    ap.add_argument("--refresh", action="store_true", help="download the current ClinVar release")
    ap.add_argument("--build", choices=["GRCh37", "GRCh38"], help="override build detection")
    ap.add_argument("--include-filtered", action="store_true", help="keep calls whose FILTER is not PASS")
    ap.add_argument("--min-qual", type=float, default=0, help="drop calls below this QUAL (default 0)")
    ap.add_argument("--include-benign", action="store_true", help="keep benign and likely benign matches")
    ap.add_argument("--genes", help="file of gene symbols; report only these")
    ap.add_argument("--exclude-genes", help="file of gene symbols never to report (patient's policy)")
    ap.add_argument("--previous", help="previous matches CSV to diff against (default: newest in out-dir)")
    ap.add_argument("--force", action="store_true", help="overwrite outputs for the same ClinVar release")
    args = ap.parse_args(argv)

    if not os.path.exists(args.vcf):
        sys.exit(f"VCF not found: {args.vcf}")
    here = Path(__file__).resolve().parent
    acmg = read_gene_list(str(here / "acmg_sf_genes.txt")) if (here / "acmg_sf_genes.txt").exists() else set()
    include = read_gene_list(args.genes)
    exclude = read_gene_list(args.exclude_genes)

    header, samples = read_header(args.vcf)
    build = args.build or detect_build(header)
    if not build:
        sys.exit("Could not determine the genome build from the VCF header; pass --build.")
    if len(samples) != 1:
        print(f"warning: VCF has {len(samples)} samples; using the first ({samples[0] if samples else 'none'})")
    print(f"VCF: {args.vcf}\n  sample {samples[0] if samples else '?'}; build {build}; "
          f"source {header_value(header, 'source') or 'unknown'}")
    print("  hashing...", end="", flush=True)
    vcf_sha = file_digest(args.vcf)
    print(f" sha256 {vcf_sha[:16]}...")

    print("Reading patient variants (one pass)...")
    patient, stats = read_patient(args.vcf, args.include_filtered, args.min_qual)
    print(f"  carried variant alleles: {len(patient):,}")

    clinvar_path = ensure_clinvar(args.clinvar_dir, build, args.refresh, args.clinvar)
    print("Streaming ClinVar against the patient's variants...")
    matches, release = stream_clinvar(clinvar_path, patient, acmg)
    if not release:
        release = dt.date.today().isoformat()
    if not args.include_benign:
        matches = [m for m in matches if m["tier"] != "benign"]
    if include:
        matches = [m for m in matches if m["gene"].upper() in include]
    if exclude:
        matches = [m for m in matches if m["gene"].upper() not in exclude]
    matches.sort(key=lambda m: (TIER_ORDER.index(m["tier"]), -int(m["stars"]), m["gene"], m["chrom"], m["pos"]))

    os.makedirs(args.out_dir, exist_ok=True)
    stem = os.path.join(args.out_dir, f"{release}_clinvar")
    if os.path.exists(stem + "_matches.csv") and not args.force:
        sys.exit(f"{stem}_matches.csv already exists for ClinVar release {release}; use --force to overwrite.")

    previous = args.previous
    if previous is None:
        older = sorted(p for p in glob.glob(os.path.join(args.out_dir, "*_clinvar_matches.csv"))
                       if os.path.basename(p) < f"{release}_clinvar_matches.csv")
        previous = older[-1] if older else None
    changes = None
    if previous:
        changes = diff_runs(read_matches(previous), matches)
        write_csv(stem + "_changes.csv", changes, CHANGE_COLUMNS)

    write_csv(stem + "_matches.csv", matches, COLUMNS)
    meta = {
        "tool": "analyze_wgs.py", "tool_version": VERSION,
        "run_at": dt.datetime.now().isoformat(timespec="seconds"),
        "vcf": {"path": os.path.abspath(args.vcf), "sha256": vcf_sha, "bytes": os.path.getsize(args.vcf),
                "sample": samples[0] if samples else "", "build": build,
                "source": header_value(header, "source"), "reference": header_value(header, "reference")},
        "clinvar": {"path": os.path.abspath(clinvar_path), "release": release,
                    "md5": file_digest(clinvar_path, "md5")},
        "filters": {"include_filtered": args.include_filtered, "min_qual": args.min_qual,
                    "include_benign": args.include_benign,
                    "genes": sorted(include), "exclude_genes_count": len(exclude)},
        "genome": genome_stats(stats),
        "matches": {"total": len(matches), "by_tier": dict(Counter(m["tier"] for m in matches)),
                    "pathogenic_2plus_stars": sum(1 for m in matches if m["tier"] == "pathogenic" and int(m["stars"]) >= 2),
                    "acmg_sf_genes_hit": sorted({m["gene"] for m in matches if m["acmg_sf"]})},
        "previous_run": os.path.abspath(previous) if previous else None,
        "changes": dict(Counter(c["change"] for c in changes)) if changes is not None else None,
        "outputs": {"matches": stem + "_matches.csv", "changes": (stem + "_changes.csv") if changes is not None else None},
    }
    with open(stem + "_run.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print_summary(stats, matches, changes, build, release)
    print(f"\nwrote {stem}_matches.csv, {stem}_run.json" + (f", {stem}_changes.csv" if changes is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
