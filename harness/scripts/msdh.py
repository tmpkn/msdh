#!/usr/bin/env python3
"""MSDH helper script. Standard library only.

Commands:
  session      declare or show the current session identity (model, runtime)
  status       record, session and git state at a glance
  check-remote verify that the origin remote looks private
  validate     validate the record against harness/schemas
  commit       validate, stage, and commit one operation with provenance
  tag          create an annotated milestone tag
  labs         rebuild data/labs_all.csv, or show a trend for one analyte
  symptoms     list distinct symptom names in symptoms/log.csv

Run from anywhere inside the record; the repository root is located
automatically.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

HARNESS_OWNED = ("AGENTS.md", "CLAUDE.md", "README.md", ".gitignore", "harness")
RECORD_DIRS = ("profile", "source", "data", "symptoms", "diags", "chats")
DATED_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_[a-z0-9_]+\.(md|csv)$")
SOURCE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_[A-Za-z0-9_.\-]+$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ASSESS_RE = re.compile(
    r"^### (\d{4}-\d{2}-\d{2}) \| (model|human|patient) \| (.+?) \| (.+)$"
)
FRONT_KEY_RE = re.compile(r"^([a-z_]+):\s*(.*)$")

COMMON_REQUIRED = ("type", "title", "date", "created", "harness", "author_kind", "author", "source")
AUTHOR_KINDS = ("model", "human", "patient")
TYPES = ("profile", "summary", "lab", "visit", "other", "symptom", "diag", "chat")
VISIT_KINDS = ("consultation", "follow_up", "procedure", "emergency", "telehealth", "other")
CHAT_KINDS = ("consultation", "review", "second_opinion", "onboarding")
OTHER_SUBTYPES = ("imaging", "pathology", "genetics", "questionnaire", "device",
                  "procedure_report", "prior_record", "correspondence", "misc")
DIAG_STATUSES = ("hypothesis", "under_investigation", "confirmed", "ruled_out", "superseded")
SYMPTOM_STATUSES = ("new", "ongoing", "improving", "worsening", "resolved")

LABS_COLUMNS = ["date", "analyte", "value", "unit", "ref_low", "ref_high", "flag", "lab", "source", "notes"]
LABS_ALL_COLUMNS = LABS_COLUMNS[:-1] + ["file", "notes"]
MEDS_COLUMNS = ["name", "dose", "route", "frequency", "start", "end", "prescriber", "reason", "source", "notes"]
SPECIALISTS_COLUMNS = ["name", "role", "institution", "since", "last_visit", "notes"]
SYMPTOM_LOG_COLUMNS = ["date", "symptom", "severity", "duration", "status", "notes", "source"]

PROFILE_SECTIONS = ["## Identity", "## Allergies and intolerances", "## Past medical history",
                    "## Surgeries and procedures", "## Family history", "## Lifestyle",
                    "## Reproductive history", "## Patient's own account"]
SUMMARY_SECTIONS = ["## Patient", "## Problem list", "## Active medications", "## Allergies",
                    "## Open hypotheses", "## Pending and recommended", "## Recent changes", "## Watch list"]
CHAT_SECTIONS = ["## Context", "## Discussed", "## Findings", "## Record changes",
                 "## For the doctors", "## Open questions"]
DIAG_SECTIONS = ["## Summary", "## Evidence", "## What would settle it", "## Assessments"]


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def find_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if (p / "AGENTS.md").exists() and (p / "harness" / "VERSION").exists():
            return p
    sys.exit("msdh: cannot locate record root (AGENTS.md + harness/VERSION)")


ROOT = find_root()
SESSION_FILE = ROOT / ".msdh" / "session.json"


def harness_version() -> str:
    return (ROOT / "harness" / "VERSION").read_text().strip()


def today() -> str:
    return dt.date.today().isoformat()


def git(*args: str, check: bool = True, capture: bool = True) -> str:
    res = subprocess.run(["git", *args], cwd=ROOT, text=True,
                         capture_output=capture)
    if check and res.returncode != 0:
        sys.exit(f"msdh: git {' '.join(args)} failed:\n{res.stderr.strip()}")
    return (res.stdout or "").strip()


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def load_session() -> dict | None:
    if not SESSION_FILE.exists():
        return None
    try:
        return json.loads(SESSION_FILE.read_text())
    except json.JSONDecodeError:
        return None


def require_session() -> dict:
    s = load_session()
    if not s:
        sys.exit("msdh: no session. Run the session-start procedure "
                 "(python3 harness/scripts/msdh.py session --model ... --runtime ...).")
    if s.get("date") != today():
        sys.exit(f"msdh: session is from {s.get('date')}, not today. Run session-start again.")
    if s.get("harness") != harness_version():
        sys.exit("msdh: session was started under a different harness version. Run session-start again.")
    return s


def valid_date(s: str) -> bool:
    if not DATE_RE.match(s or ""):
        return False
    try:
        dt.date.fromisoformat(s)
        return True
    except ValueError:
        return False


def parse_frontmatter(path: Path) -> tuple[dict | None, str, str | None]:
    """Return (frontmatter dict, body, error)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "missing frontmatter (file must start with ---)"
    fm: dict[str, str] = {}
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return fm, "\n".join(lines[i + 1:]), None
        if not line.strip():
            continue
        m = FRONT_KEY_RE.match(line)
        if not m:
            return None, text, f"bad frontmatter line {i + 1}: {line!r}"
        val = m.group(2).strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        fm[m.group(1)] = val
    return None, text, "unterminated frontmatter"


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        rows = list(reader)
    return list(header), rows


def load_analytes() -> dict[str, str]:
    """alias (lowercase) -> canonical name."""
    out: dict[str, str] = {}
    p = ROOT / "harness" / "schemas" / "analytes.csv"
    if not p.exists():
        return out
    _, rows = read_csv(p)
    for r in rows:
        canon = r["analyte"].strip().lower()
        out[canon] = canon
        for a in (r.get("aliases") or "").split("|"):
            a = a.strip().lower()
            if a:
                out[a] = canon
    return out


def section_headers(body: str) -> list[str]:
    return [ln.rstrip() for ln in body.splitlines() if ln.startswith("## ")]


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, path: Path | str, msg: str) -> None:
        self.errors.append(f"{path}: {msg}")

    def warn(self, path: Path | str, msg: str) -> None:
        self.warnings.append(f"{path}: {msg}")


def check_common(fm: dict, path: Path, rep: Report, expect_type: str, dated: bool) -> None:
    r = rel(path)
    for k in COMMON_REQUIRED:
        if k not in fm or fm[k] == "":
            rep.err(r, f"missing frontmatter key '{k}'")
    if fm.get("type") != expect_type:
        rep.err(r, f"type is '{fm.get('type')}', expected '{expect_type}'")
    for k in ("date", "created"):
        if k in fm and not valid_date(fm[k]):
            rep.err(r, f"'{k}' is not a valid YYYY-MM-DD date: {fm[k]!r}")
    if dated:
        m = DATED_RE.match(path.name)
        if m and fm.get("date") and m.group(1) != fm["date"]:
            rep.err(r, f"filename date {m.group(1)} != frontmatter date {fm['date']}")
    if "harness" in fm and not SEMVER_RE.match(fm["harness"]):
        rep.err(r, f"'harness' is not a version: {fm['harness']!r}")
    kind = fm.get("author_kind")
    if kind and kind not in AUTHOR_KINDS:
        rep.err(r, f"author_kind must be one of {AUTHOR_KINDS}, got {kind!r}")
    if kind == "model" and not fm.get("author_runtime"):
        rep.err(r, "author_kind is model but 'author_runtime' is missing")
    if kind == "patient" and fm.get("author") not in (None, "patient"):
        rep.err(r, "author_kind is patient but author is not 'patient'")
    src = fm.get("source", "")
    if src and src != "none":
        for s in [x.strip() for x in src.split(",") if x.strip()]:
            if not (ROOT / s).exists():
                rep.err(r, f"source path does not exist: {s}")


def check_sections(body: str, path: Path, rep: Report, required: list[str]) -> None:
    present = section_headers(body)
    for s in required:
        if s not in present:
            rep.err(rel(path), f"missing section '{s}'")


def check_filename(path: Path, rep: Report) -> str | None:
    m = DATED_RE.match(path.name)
    if not m:
        rep.err(rel(path), "filename must be YYYY-MM-DD_slug.md|csv (lowercase, underscores)")
        return None
    if not valid_date(m.group(1)):
        rep.err(rel(path), f"filename date is invalid: {m.group(1)}")
        return None
    return m.group(1)


def check_csv_header(path: Path, rep: Report, expected: list[str]) -> list[dict] | None:
    try:
        header, rows = read_csv(path)
    except Exception as e:  # noqa: BLE001
        rep.err(rel(path), f"cannot parse CSV: {e}")
        return None
    if header != expected:
        rep.err(rel(path), f"header must be exactly: {','.join(expected)}")
        return None
    return rows


def md_files(d: Path) -> list[Path]:
    return sorted(p for p in d.glob("*.md") if p.is_file())


def validate_profile(rep: Report) -> bool:
    d = ROOT / "profile"
    prof = d / "profile.md"
    if not prof.exists():
        return False
    fm, body, e = parse_frontmatter(prof)
    if e:
        rep.err(rel(prof), e)
    else:
        check_common(fm, prof, rep, "profile", dated=False)
        check_sections(body, prof, rep, PROFILE_SECTIONS)
    for name, cols in (("medications.csv", MEDS_COLUMNS), ("specialists.csv", SPECIALISTS_COLUMNS)):
        p = d / name
        if not p.exists():
            rep.err(rel(p), "missing (create it with the header row even if empty)")
            continue
        rows = check_csv_header(p, rep, cols)
        if rows is None:
            continue
        for i, row in enumerate(rows, start=2):
            for col in ("start", "end", "since", "last_visit"):
                if col in row and row[col] and not valid_date(row[col]):
                    rep.err(rel(p), f"row {i}: '{col}' is not a date: {row[col]!r}")
            if "name" in row and not row["name"].strip():
                rep.err(rel(p), f"row {i}: empty name")
    for p in d.iterdir():
        if p.name not in ("profile.md", "medications.csv", "specialists.csv", ".gitkeep"):
            rep.err(rel(p), "unexpected file in profile/")
    return True


def validate_summary(rep: Report, onboarded: bool) -> None:
    p = ROOT / "SUMMARY.md"
    if not p.exists():
        if onboarded:
            rep.warn("SUMMARY.md", "missing; run summary-refresh")
        return
    fm, body, e = parse_frontmatter(p)
    if e:
        rep.err("SUMMARY.md", e)
        return
    check_common(fm, p, rep, "summary", dated=False)
    if not fm.get("record_commit"):
        rep.err("SUMMARY.md", "missing 'record_commit'")
    check_sections(body, p, rep, SUMMARY_SECTIONS)


def validate_labs(rep: Report, analytes: dict[str, str]) -> list[dict]:
    d = ROOT / "data" / "labs"
    all_rows: list[dict] = []
    csvs = sorted(d.glob("*.csv"))
    mds = {p.stem: p for p in md_files(d)}
    for c in csvs:
        fdate = check_filename(c, rep)
        rows = check_csv_header(c, rep, LABS_COLUMNS)
        if rows is None:
            continue
        sib = mds.pop(c.stem, None)
        if sib is None:
            rep.err(rel(c), f"missing sibling provenance file {c.stem}.md")
        else:
            fm, body, e = parse_frontmatter(sib)
            if e:
                rep.err(rel(sib), e)
            else:
                check_common(fm, sib, rep, "lab", dated=True)
                if not fm.get("lab"):
                    rep.err(rel(sib), "missing 'lab'")
                check_sections(body, sib, rep, ["## Report notes", "## Transcription notes"])
        if not rows:
            rep.err(rel(c), "no data rows")
        for i, row in enumerate(rows, start=2):
            if fdate and row["date"] != fdate:
                rep.err(rel(c), f"row {i}: date {row['date']!r} != filename date {fdate}")
            if not row["analyte"].strip():
                rep.err(rel(c), f"row {i}: empty analyte")
            elif row["analyte"] != row["analyte"].strip().lower():
                rep.err(rel(c), f"row {i}: analyte must be lowercase canonical name: {row['analyte']!r}")
            elif analytes and row["analyte"] not in analytes:
                rep.warn(rel(c), f"row {i}: analyte {row['analyte']!r} not in harness/schemas/analytes.csv")
            elif analytes.get(row["analyte"]) != row["analyte"]:
                rep.err(rel(c), f"row {i}: {row['analyte']!r} is an alias; use canonical {analytes[row['analyte']]!r}")
            if row["value"].strip() == "":
                rep.err(rel(c), f"row {i}: empty value")
            if row["flag"] not in ("", "H", "L", "A"):
                rep.err(rel(c), f"row {i}: flag must be H, L, A or empty, got {row['flag']!r}")
            if not row["lab"].strip():
                rep.err(rel(c), f"row {i}: empty lab")
            if not row["source"].strip() or not (ROOT / row["source"]).exists():
                rep.err(rel(c), f"row {i}: source path missing or does not exist: {row['source']!r}")
            r2 = dict(row)
            r2["file"] = rel(c)
            all_rows.append(r2)
    for stem, p in mds.items():
        rep.err(rel(p), f"provenance file without a sibling {stem}.csv")
    for p in d.iterdir():
        if p.suffix not in (".csv", ".md") and p.name != ".gitkeep":
            rep.err(rel(p), "unexpected file in data/labs/")
    return all_rows


def labs_all_text(rows: list[dict]) -> str:
    rows = sorted(rows, key=lambda r: (r["analyte"], r["date"], r["file"]))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=LABS_ALL_COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in LABS_ALL_COLUMNS})
    return buf.getvalue()


def validate_labs_all(rep: Report, rows: list[dict]) -> None:
    p = ROOT / "data" / "labs_all.csv"
    expected = labs_all_text(rows)
    if not p.exists():
        if rows:
            rep.err("data/labs_all.csv", "missing; run `msdh.py labs rebuild`")
        return
    if p.read_text(encoding="utf-8") != expected:
        rep.err("data/labs_all.csv", "stale or hand-edited; run `msdh.py labs rebuild`")


def validate_md_dir(rep: Report, d: Path, expect_type: str, extra) -> None:
    for p in d.iterdir():
        if p.name == ".gitkeep":
            continue
        if p.suffix != ".md":
            if expect_type == "other" and p.suffix == ".csv" and (d / (p.stem + ".md")).exists():
                continue
            rep.err(rel(p), f"unexpected file in {rel(d)}/")
            continue
        check_filename(p, rep)
        fm, body, e = parse_frontmatter(p)
        if e:
            rep.err(rel(p), e)
            continue
        check_common(fm, p, rep, expect_type, dated=True)
        extra(fm, body, p)


def extra_visit(fm: dict, body: str, p: Path, rep: Report) -> None:
    for k in ("clinician", "clinician_role", "visit_kind"):
        if not fm.get(k):
            rep.err(rel(p), f"missing '{k}'")
    if fm.get("visit_kind") and fm["visit_kind"] not in VISIT_KINDS:
        rep.err(rel(p), f"visit_kind must be one of {VISIT_KINDS}")
    check_sections(body, p, rep, ["## Reason for visit", "## Clinician's findings",
                                  "## Clinician's assessment", "## Plan"])


def extra_other(fm: dict, body: str, p: Path, rep: Report) -> None:
    if fm.get("subtype") not in OTHER_SUBTYPES:
        rep.err(rel(p), f"subtype must be one of {OTHER_SUBTYPES}, got {fm.get('subtype')!r}")
    check_sections(body, p, rep, ["## Summary", "## Findings"])


def extra_symptom(fm: dict, body: str, p: Path, rep: Report) -> None:
    check_sections(body, p, rep, ["## Logged"])


def extra_chat(fm: dict, body: str, p: Path, rep: Report) -> None:
    if fm.get("visit_kind") not in CHAT_KINDS:
        rep.err(rel(p), f"visit_kind must be one of {CHAT_KINDS}, got {fm.get('visit_kind')!r}")
    check_sections(body, p, rep, CHAT_SECTIONS)


def extra_diag(fm: dict, body: str, p: Path, rep: Report) -> None:
    r = rel(p)
    st = fm.get("status")
    if st not in DIAG_STATUSES:
        rep.err(r, f"status must be one of {DIAG_STATUSES}, got {st!r}")
    for k in ("status_date", "status_by", "fields"):
        if not fm.get(k):
            rep.err(r, f"missing '{k}'")
    if fm.get("status_date") and not valid_date(fm["status_date"]):
        rep.err(r, f"status_date is not a date: {fm['status_date']!r}")
    if st == "superseded":
        sb = fm.get("superseded_by", "")
        if not sb or not (ROOT / sb).exists():
            rep.err(r, "status is superseded but 'superseded_by' is missing or does not exist")
    check_sections(body, p, rep, DIAG_SECTIONS)
    # assessments
    lines = body.splitlines()
    try:
        start = lines.index("## Assessments")
    except ValueError:
        return
    count = 0
    last_date = ""
    for ln in lines[start + 1:]:
        if ln.startswith("## "):
            break
        if ln.startswith("### "):
            m = ASSESS_RE.match(ln)
            if not m:
                rep.err(r, f"bad assessment header (need 'YYYY-MM-DD | kind | author | runtime-or-source'): {ln!r}")
                continue
            count += 1
            d, kind, author, tail = m.groups()
            if not valid_date(d):
                rep.err(r, f"assessment date invalid: {d}")
            elif d < last_date:
                rep.err(r, f"assessments must be in chronological order; {d} comes after {last_date}")
            last_date = max(last_date, d)
            if kind in ("human", "patient"):
                if not (ROOT / tail.strip()).exists():
                    rep.err(r, f"assessment {d} by {author}: source path does not exist: {tail.strip()!r}")
                if kind == "patient" and author != "patient":
                    rep.err(r, f"assessment {d}: kind patient requires author 'patient'")
    if count == 0:
        rep.err(r, "no assessments under '## Assessments'")
    if st == "confirmed":
        confirmed_by_human = any(
            ASSESS_RE.match(ln) and ASSESS_RE.match(ln).group(2) == "human"
            for ln in lines[start + 1:]
        )
        if not confirmed_by_human:
            rep.err(r, "status confirmed requires at least one human assessment")


def validate_symptom_log(rep: Report) -> None:
    p = ROOT / "symptoms" / "log.csv"
    if not p.exists():
        return
    rows = check_csv_header(p, rep, SYMPTOM_LOG_COLUMNS)
    if rows is None:
        return
    for i, row in enumerate(rows, start=2):
        if not valid_date(row["date"]):
            rep.err(rel(p), f"row {i}: bad date {row['date']!r}")
        if not row["symptom"].strip() or row["symptom"] != row["symptom"].strip().lower():
            rep.err(rel(p), f"row {i}: symptom must be a lowercase short name, got {row['symptom']!r}")
        if row["severity"]:
            try:
                sv = int(row["severity"])
                if not 0 <= sv <= 10:
                    raise ValueError
            except ValueError:
                rep.err(rel(p), f"row {i}: severity must be 0-10 or empty, got {row['severity']!r}")
        if row["status"] not in SYMPTOM_STATUSES:
            rep.err(rel(p), f"row {i}: status must be one of {SYMPTOM_STATUSES}, got {row['status']!r}")
        if row["source"] and not (ROOT / row["source"]).exists():
            rep.err(rel(p), f"row {i}: source path does not exist: {row['source']!r}")


def validate_source(rep: Report) -> None:
    d = ROOT / "source"
    for p in d.iterdir():
        if p.name == ".gitkeep":
            continue
        if not SOURCE_RE.match(p.name):
            rep.warn(rel(p), "source files should be named YYYY-MM-DD_slug.ext")


def validate_tree(rep: Report) -> None:
    allowed_root = set(HARNESS_OWNED) | set(RECORD_DIRS) | {"SUMMARY.md", ".git", ".msdh", "scratch"}
    for p in ROOT.iterdir():
        if p.name not in allowed_root:
            rep.err(p.name, "unexpected file or directory at record root")
    for p in (ROOT / "data").iterdir():
        if p.name not in ("labs", "visits", "other", "labs_all.csv", ".gitkeep"):
            rep.err(rel(p), "unexpected file in data/")


def run_validation() -> Report:
    rep = Report()
    validate_tree(rep)
    onboarded = validate_profile(rep)
    validate_summary(rep, onboarded)
    analytes = load_analytes()
    rows = validate_labs(rep, analytes)
    validate_labs_all(rep, rows)
    validate_md_dir(rep, ROOT / "data" / "visits", "visit", lambda fm, b, p: extra_visit(fm, b, p, rep))
    validate_md_dir(rep, ROOT / "data" / "other", "other", lambda fm, b, p: extra_other(fm, b, p, rep))
    validate_md_dir(rep, ROOT / "diags", "diag", lambda fm, b, p: extra_diag(fm, b, p, rep))
    validate_md_dir(rep, ROOT / "chats", "chat", lambda fm, b, p: extra_chat(fm, b, p, rep))
    # symptoms: journal entries plus log.csv
    sd = ROOT / "symptoms"
    for p in sd.iterdir():
        if p.name in (".gitkeep", "log.csv"):
            continue
        if p.suffix != ".md":
            rep.err(rel(p), "unexpected file in symptoms/")
            continue
        check_filename(p, rep)
        fm, body, e = parse_frontmatter(p)
        if e:
            rep.err(rel(p), e)
            continue
        check_common(fm, p, rep, "symptom", dated=True)
        extra_symptom(fm, body, p, rep)
    validate_symptom_log(rep)
    validate_source(rep)
    return rep


def cmd_validate(args) -> int:
    rep = run_validation()
    for w in rep.warnings:
        print(f"WARN  {w}")
    for e in rep.errors:
        print(f"ERROR {e}")
    n_e, n_w = len(rep.errors), len(rep.warnings)
    print(f"validate: {n_e} error(s), {n_w} warning(s)")
    return 1 if n_e else 0


# --------------------------------------------------------------------------
# session / status / remote
# --------------------------------------------------------------------------

def cmd_session(args) -> int:
    if args.model or args.runtime:
        if not (args.model and args.runtime):
            sys.exit("msdh: --model and --runtime must be given together")
        existing = load_session()
        if existing and existing.get("date") == today() and existing.get("model") != args.model:
            print(f"note: replacing today's session identity {existing.get('model')} -> {args.model}")
        SESSION_FILE.parent.mkdir(exist_ok=True)
        s = {"model": args.model.strip(), "runtime": args.runtime.strip(),
             "date": today(), "harness": harness_version(),
             "started": dt.datetime.now().isoformat(timespec="seconds")}
        SESSION_FILE.write_text(json.dumps(s, indent=2) + "\n")
        print(f"session: {s['model']} on {s['runtime']}, harness {s['harness']}, {s['date']}")
        return 0
    s = load_session()
    if not s:
        print("session: none")
        return 1
    stale = " (STALE: not today)" if s.get("date") != today() else ""
    print(f"session: {s.get('model')} on {s.get('runtime')}, harness {s.get('harness')}, {s.get('date')}{stale}")
    return 1 if stale else 0


def record_stats() -> dict[str, int]:
    def n(d: str, pat: str) -> int:
        return len([p for p in (ROOT / d).glob(pat) if p.name != ".gitkeep"])
    return {
        "source files": n("source", "*"),
        "lab panels": n("data/labs", "*.csv"),
        "visits": n("data/visits", "*.md"),
        "other": n("data/other", "*.md"),
        "symptom entries": n("symptoms", "*.md"),
        "diags": n("diags", "*.md"),
        "chats": n("chats", "*.md"),
    }


def cmd_status(args) -> int:
    print(f"root:     {ROOT}")
    print(f"harness:  {harness_version()}")
    s = load_session()
    if s:
        stale = "  <- STALE" if s.get("date") != today() else ""
        print(f"session:  {s.get('model')} on {s.get('runtime')} ({s.get('date')}){stale}")
    else:
        print("session:  none  <- run session-start")
    onboarded = (ROOT / "profile" / "profile.md").exists()
    print(f"profile:  {'present' if onboarded else 'MISSING (not onboarded)'}")
    print(f"summary:  {'present' if (ROOT / 'SUMMARY.md').exists() else 'missing'}")
    branch = git("rev-parse", "--abbrev-ref", "HEAD", check=False) or "(no commits yet)"
    print(f"branch:   {branch}")
    head = git("log", "-1", "--format=%h %ad %s", "--date=short", check=False)
    print(f"head:     {head or '(no commits yet)'}")
    porcelain = git("status", "--porcelain", check=False)
    if porcelain:
        print("tree:     DIRTY")
        for ln in porcelain.splitlines():
            print(f"          {ln}")
    else:
        print("tree:     clean")
    remotes = git("remote", "-v", check=False)
    print("remotes:  " + (remotes.replace("\n", "\n          ") if remotes else "none"))
    stats = record_stats()
    print("record:   " + ", ".join(f"{v} {k}" for k, v in stats.items()))
    return 0


def http_status(url: str) -> int | None:
    req = urllib.request.Request(url, headers={"User-Agent": "msdh", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:  # noqa: BLE001
        return None


def parse_remote(url: str) -> tuple[str, str] | None:
    """Return (host, owner/repo) for common git URL shapes."""
    m = re.match(r"^(?:ssh://)?git@([^:/]+)[:/](.+?)(?:\.git)?/?$", url)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"^https?://(?:[^@/]+@)?([^/]+)/(.+?)(?:\.git)?/?$", url)
    if m:
        return m.group(1), m.group(2)
    return None


def cmd_check_remote(args) -> int:
    url = git("remote", "get-url", "origin", check=False)
    if not url:
        print("check-remote: no 'origin' remote. The record has no backup; add a PRIVATE remote.")
        return 1
    parsed = parse_remote(url)
    if not parsed:
        print(f"check-remote: cannot parse origin URL {url!r}; confirm with the patient that it is private.")
        return 2
    host, path = parsed
    print(f"origin: {url}")
    if host == "github.com":
        code = http_status(f"https://api.github.com/repos/{path}")
        if code == 200:
            print("check-remote: FAIL origin is a PUBLIC GitHub repository. Do not push.")
            return 1
        if code == 404:
            print("check-remote: OK origin is not visible anonymously on GitHub (private or nonexistent).")
            return 0
    elif "gitlab" in host or args.gitlab:
        code = http_status(f"https://{host}/api/v4/projects/{urllib.parse.quote(path, safe='')}")
        if code == 200:
            print("check-remote: FAIL origin is a PUBLIC GitLab project. Do not push.")
            return 1
        if code == 404:
            print("check-remote: OK origin is not visible anonymously on GitLab (private or nonexistent).")
            return 0
        if code == 401:
            print("check-remote: OK host requires authentication for any project lookup.")
            return 0
    print("check-remote: cannot verify visibility automatically; confirm with the patient that origin is private.")
    return 2


# --------------------------------------------------------------------------
# commit / tag
# --------------------------------------------------------------------------

def is_harness_owned(path: str) -> bool:
    top = path.split("/", 1)[0]
    return top in HARNESS_OWNED


def cmd_commit(args) -> int:
    s = require_session()
    if args.harness_update:
        pass
    rep = run_validation()
    for w in rep.warnings:
        print(f"WARN  {w}")
    if rep.errors:
        for e in rep.errors:
            print(f"ERROR {e}")
        print(f"commit: refused, {len(rep.errors)} validation error(s). Fix them first.")
        return 1

    if args.all:
        git("add", "-A")
    elif args.paths:
        git("add", "--", *args.paths)
    else:
        sys.exit("msdh: give the paths to commit, or --all")

    staged = git("diff", "--cached", "--name-only").splitlines()
    if not staged:
        print("commit: nothing staged.")
        return 1
    owned = [p for p in staged if is_harness_owned(p)]
    record = [p for p in staged if not is_harness_owned(p)]
    if owned and not args.harness_update:
        git("reset", "-q")
        print("commit: refused. These harness-owned paths were about to be committed:")
        for p in owned:
            print(f"  {p}")
        print("Patient sessions never modify the harness. Revert them (git checkout -- <path>).")
        return 1
    if args.harness_update and record:
        git("reset", "-q")
        print("commit: refused. A harness update must not include record files:")
        for p in record:
            print(f"  {p}")
        return 1

    body = "\n".join([
        f"Procedure: {args.procedure}",
        f"Model: {s['model']}",
        f"Runtime: {s['runtime']}",
        f"Harness: {harness_version()}",
    ])
    message = f"{args.procedure}: {args.message.strip()}\n\n{body}\n"
    print(git("diff", "--cached", "--stat"))
    if args.dry_run:
        git("reset", "-q")
        print("--- message ---")
        print(message)
        print("commit: dry run, nothing committed (changes unstaged again).")
        return 0
    res = subprocess.run(["git", "commit", "-q", "-F", "-"], cwd=ROOT, text=True,
                         input=message, capture_output=True)
    if res.returncode != 0:
        print(res.stderr.strip())
        print("commit: git commit failed.")
        return 1
    print(git("log", "-1", "--format=committed %h: %s"))
    return 0


def cmd_tag(args) -> int:
    s = require_session()
    if git("status", "--porcelain", check=False):
        print("tag: refused, working tree is dirty. Commit first.")
        return 1
    name = args.name
    if not re.match(r"^[a-z0-9][a-z0-9._-]*$", name):
        print("tag: name must be lowercase letters, digits, dots, dashes, underscores")
        return 1
    msg = f"{args.message.strip()}\n\nModel: {s['model']}\nRuntime: {s['runtime']}\nHarness: {harness_version()}\n"
    res = subprocess.run(["git", "tag", "-a", name, "-F", "-"], cwd=ROOT, text=True,
                         input=msg, capture_output=True)
    if res.returncode != 0:
        print(res.stderr.strip())
        return 1
    print(f"tag: created {name}")
    return 0


# --------------------------------------------------------------------------
# labs / symptoms
# --------------------------------------------------------------------------

def collect_lab_rows() -> list[dict]:
    rows: list[dict] = []
    for c in sorted((ROOT / "data" / "labs").glob("*.csv")):
        header, rs = read_csv(c)
        if header != LABS_COLUMNS:
            sys.exit(f"msdh: {rel(c)} has a bad header; run validate")
        for r in rs:
            r2 = dict(r)
            r2["file"] = rel(c)
            rows.append(r2)
    return rows


def cmd_labs(args) -> int:
    if args.labs_cmd == "rebuild":
        rows = collect_lab_rows()
        p = ROOT / "data" / "labs_all.csv"
        p.write_text(labs_all_text(rows), encoding="utf-8")
        print(f"labs rebuild: {len(rows)} rows from {len(set(r['file'] for r in rows))} file(s) -> data/labs_all.csv")
        return 0
    if args.labs_cmd == "trend":
        analytes = load_analytes()
        key = args.analyte.strip().lower()
        canon = analytes.get(key, key)
        rows = [r for r in collect_lab_rows() if r["analyte"] == canon]
        if args.since:
            rows = [r for r in rows if r["date"] >= args.since]
        rows.sort(key=lambda r: r["date"])
        if not rows:
            print(f"trend: no rows for {canon!r}")
            return 1
        print(f"analyte: {canon}")
        print(f"{'date':<12}{'value':>10}  {'unit':<10}{'ref':<16}{'flag':<5}{'lab':<14}file")
        for r in rows:
            ref = f"{r['ref_low']}-{r['ref_high']}" if (r['ref_low'] or r['ref_high']) else ""
            print(f"{r['date']:<12}{r['value']:>10}  {r['unit']:<10}{ref:<16}{r['flag']:<5}{r['lab']:<14}{r['file']}")
        return 0
    if args.labs_cmd == "list":
        rows = collect_lab_rows()
        seen: dict[str, tuple[int, str, str]] = {}
        for r in rows:
            n, first, last = seen.get(r["analyte"], (0, r["date"], r["date"]))
            seen[r["analyte"]] = (n + 1, min(first, r["date"]), max(last, r["date"]))
        for a in sorted(seen):
            n, first, last = seen[a]
            print(f"{a:<34}{n:>4}  {first} .. {last}")
        return 0
    return 1


def cmd_symptoms(args) -> int:
    p = ROOT / "symptoms" / "log.csv"
    if not p.exists():
        print("symptoms: no log.csv yet")
        return 0
    _, rows = read_csv(p)
    latest: dict[str, dict] = {}
    for r in rows:
        if r["symptom"] not in latest or r["date"] >= latest[r["symptom"]]["date"]:
            latest[r["symptom"]] = r
    for name in sorted(latest):
        r = latest[name]
        print(f"{name:<28}{r['status']:<12}last {r['date']}  sev {r['severity'] or '-'}")
    return 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="msdh.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("session", help="declare or show the session identity")
    p.add_argument("--model", help="exact model id, e.g. claude-fable-5-1")
    p.add_argument("--runtime", help="agent runtime and version, e.g. 'claude-code 2.1.0'")
    p.set_defaults(fn=cmd_session)

    p = sub.add_parser("status", help="record, session and git state")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("check-remote", help="verify origin looks private")
    p.add_argument("--gitlab", action="store_true", help="treat the host as a GitLab instance")
    p.set_defaults(fn=cmd_check_remote)

    p = sub.add_parser("validate", help="validate the record against the schemas")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("commit", help="validate, stage and commit one operation")
    p.add_argument("--procedure", required=True,
                   help="procedure name: onboarding, ingest, visit, adhoc, second-opinion, summary-refresh, correction, harness-update")
    p.add_argument("-m", "--message", required=True, help="one-line subject")
    p.add_argument("--all", action="store_true", help="stage every change outside harness-owned paths")
    p.add_argument("--harness-update", action="store_true", help="allow (only) harness-owned paths")
    p.add_argument("--dry-run", action="store_true", help="show what would be committed")
    p.add_argument("paths", nargs="*", help="paths to stage")
    p.set_defaults(fn=cmd_commit)

    p = sub.add_parser("tag", help="create an annotated milestone tag")
    p.add_argument("name")
    p.add_argument("-m", "--message", required=True)
    p.set_defaults(fn=cmd_tag)

    p = sub.add_parser("labs", help="lab table tools")
    ls = p.add_subparsers(dest="labs_cmd", required=True)
    ls.add_parser("rebuild", help="regenerate data/labs_all.csv")
    ls.add_parser("list", help="list analytes with counts and date span")
    t = ls.add_parser("trend", help="print every value of one analyte over time")
    t.add_argument("analyte")
    t.add_argument("--since", help="YYYY-MM-DD")
    p.set_defaults(fn=cmd_labs)

    p = sub.add_parser("symptoms", help="list symptom names with latest status")
    p.set_defaults(fn=cmd_symptoms)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
