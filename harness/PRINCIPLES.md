# MSDH Principles

This is the design the harness is built on. Procedures and schemas implement
it. When a procedure is silent on something, decide in the spirit of these
principles.

## 1. Purpose

MSDH gives a patient who already has access to specialists and tests the one
thing they are missing: a holistic physician who knows their entire history.
Specialists see their own slice. The harness sees the union of symptoms, test
results and specialist conclusions over time, and surfaces cross-field
patterns. Its outputs are hypotheses and questions to take back to doctors,
never diagnoses that replace them.

Two modes of use, both first-class:

- **Visits.** Meaningful consultations, equivalent to a doctor visit. These are
  summarized and recorded in `chats/`.
- **Ad-hoc questions.** Quick questions answered with the full record in mind,
  as if asked of a physician who knows the patient. Not summarized, but any
  new fact they reveal is recorded.

## 2. Raw agentic environment

Version 1.x has no user interface. The harness is a directory of markdown and
CSV files plus procedures that any capable LLM agent follows from a terminal
session opened in the record directory. Code exists only as auxiliary,
deterministic helpers: validation, table rebuilding, trend extraction.

The harness is agent-agnostic. `AGENTS.md` is the entry point. `CLAUDE.md`
merely points to it. The same record is meant to be opened by different agents
and models, and that diversity is a feature: see second opinions.

## 3. Provenance is mandatory

Every file produced by reasoning carries who produced it:

- for a model: the exact model identifier, the runtime (agent harness and
  version), the date and the MSDH harness version;
- for a human doctor: name, role, and a link to the source document;
- for the patient: marked as patient-reported.

Models are unreliable narrators of their own identity. The session-start
procedure therefore asks the patient to confirm the model identity once per
session, with the agent's best guess offered as the default. That identity is
stamped on everything written in the session.

Diagnosis entries are multi-voiced: one file per hypothesis, holding dated
assessments from different authors, human and model. Agreement and
disagreement between voices is visible data.

## 4. Version control is the content guard

The record is a git repository and git is part of the design, not an
afterthought. An agent that misunderstands the harness can produce at worst
one obviously wrong commit, visible and revertible.

- One operation, one commit. Never mixed.
- Commit messages carry provenance: procedure, model, runtime, harness version.
- Clean tree at session start. A dirty tree is inspected, never absorbed.
- Validation runs before every commit. Invalid files never enter history.
- The agent shows what it is about to commit. The patient is the last gate.
- History is append-only. No amend, rebase or force push. Corrections are new
  commits; record entries are superseded, never deleted.
- Milestones are tagged.

The patient's remote must be private. The record contains protected health
information. The harness checks what it can and otherwise asks the patient to
confirm.

## 5. Harness and record are separable

The harness upstream repository contains only `AGENTS.md`, `CLAUDE.md`,
`README.md`, `.gitignore`, `harness/`, and empty record directories. A patient
record is a clone of it with its own private origin and the harness repository
kept as an `upstream` remote. Updating the harness is a pull from upstream.

Guarantees that make this conflict-free:

- the upstream never changes files outside the harness-owned set once a
  version is released;
- patient sessions never change files inside the harness-owned set;
- every processed file records the harness version that produced it, so
  migrations know what they are migrating.

## 6. Layout conventions

- **Type-first, date in the filename.** `data/labs/2026-11-02_quest_cbc.csv`,
  not `data/2026/11/02/`. A directory listing shows one kind of thing in
  chronological order.
- **Dates are ISO 8601**, `YYYY-MM-DD`, everywhere: filenames, frontmatter,
  CSV columns. Filenames are lowercase, words joined by underscores.
- **Markdown for narrative, CSV for anything that will be queried over time.**
  Labs, symptoms and medications each have a structured table beside the
  narrative files.
- **Derived tables are regenerated, never hand-edited.** `data/labs_all.csv`
  is rebuilt by script from the per-source files and committed so that agents
  without script access can still read it.
- **`source/` is immutable.** Processed files point back to their source by
  path.
- **Bulk data stays outside.** Sequencing files live behind a gitignored
  `dna/` symlink. Only derived, dated outputs enter `source/`, produced by
  tools the patient runs by hand outside the agent.
- **`SUMMARY.md` is the physician's working memory.** Roughly one page:
  problem list, active medications, open hypotheses, pending tests, recent
  changes. It is what gets loaded for every ad-hoc question, and it is
  rewritten after every change to the record.

## 7. Clinical conduct

- Think like a generalist who reads everything. The point is the connection
  between the cardiology letter and the thyroid panel and the symptom journal.
- Separate observation from inference, and label confidence.
- Anything that looks urgent is said first, plainly, with the advice to seek
  care now. Then the rest.
- Questions for doctors are concrete: which specialist, what to ask, which
  test to request and why.
- When the record does not support an answer, say so. Do not fill gaps with
  population averages dressed as patient facts.
