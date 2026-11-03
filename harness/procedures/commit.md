# Procedure: commit

Every change to the record enters history through this procedure and the
`msdh.py commit` command. Never run `git commit` yourself. Never amend,
rebase, reset history, force push, or delete record files.

One operation, one commit. An ingest, a visit, a summary refresh, a
diagnosis update, a correction: each is its own commit. If an operation
naturally produces two kinds of change (a visit plus the summary refresh it
triggers), that is two commits, in that order.

## 1. Know what you changed

Before committing you must be able to name every file this operation created
or changed. `git status --porcelain` shows the tree; everything in it must
be either this operation's work or something you can explain. Unexplained
changes mean stop and ask.

## 2. Rebuild derived tables

If any file in `data/labs/` was created or changed:

```
python3 harness/scripts/msdh.py labs rebuild
```

and include `data/labs_all.csv` in the commit.

## 3. Validate

```
python3 harness/scripts/msdh.py validate
```

Fix every error. Errors are schema violations in files you just wrote; the
message names the file and the problem. Do not work around the validator and
do not touch `harness/` to make it pass.

## 4. Show the patient

Present what is about to be committed in plain language, two to five lines:
which files, what they contain, one line per new fact of consequence (a new
hypothesis, a medication change, a flagged lab value). Then wait for the
patient to say yes. The patient is the last gate. One confirmation may
cover a multi-commit operation if you said up front it would be more than
one commit.

For long operations in which the patient has already seen and approved each
piece as it was produced, a one-line "committing the visit now" is enough.

## 5. Commit

```
python3 harness/scripts/msdh.py commit --procedure <name> -m "<subject>" <paths...>
```

- `<name>` is the procedure that did the work: `onboarding`, `ingest`,
  `visit`, `adhoc`, `second-opinion`, `summary-refresh`, `correction`,
  `migration`.
- `<subject>` is one line, under 70 characters, saying what, not how.
  Examples: `Quest CBC and metabolic panel 2026-11-02`, `cardiology
  follow-up with Dr Smith 2026-10-15`, `consultation on fatigue and
  palpitations`, `refresh after ingest of 2026-11-02 labs`.
- `<paths>` are the files of this operation. Use `--all` only when you have
  verified in step 1 that every change in the tree belongs to this
  operation.

The command validates again, refuses harness-owned paths, stamps the
message with your model, runtime and harness version, shows the stat, and
commits. `--dry-run` shows the message and stat without committing.

## 6. Push

If check-remote said `OK` at session start, or the patient confirmed the
remote is private:

```
git push origin HEAD
```

Never `--force`. If the push is rejected because the remote has commits you
do not have, stop and tell the patient; do not pull or merge on your own.

## 7. Tag milestones

When a `diags/` entry changes to `confirmed` or `ruled_out`, or a
second-opinion round is complete, tag after the commit:

```
python3 harness/scripts/msdh.py tag <name> -m "<one line>"
```

Names are lowercase with dashes: `confirmed-hashimotos-2026-11-03`,
`second-opinion-round-1`. Push tags with `git push origin --tags`.

## Corrections

A correction is a commit that fixes a mistake in an earlier commit: a wrong
value, a misattributed assessment, a file that fails validation. Rules:

- Fix the file in place. Record files are never deleted; a file that should
  not exist is left in place with its status set to `superseded` or a
  `## Correction` note explaining, and the subject says so.
- The subject starts with what was wrong: `fix ferritin unit in 2026-11-02
  quest panel`.
- `diags/` assessments are not edited. A mistaken assessment is answered by
  a new assessment that says what was wrong.
- If the correction changes a fact in the summary, follow with a
  summary-refresh commit.
