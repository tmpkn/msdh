# Procedure: second-opinion

An independent assessment of the record by a model that has not seen the
existing hypotheses. Meant to be run from a different model or runtime than
the one that wrote the current assessments, and it is useful even when it
is not. The patient asks for it at the start of a session, before context
is loaded, because the point is to read the primary data blind.

Precondition: session-start steps 1 to 5 completed. **Step 6 (load the
patient) must not have been done.** If you have already read `SUMMARY.md`,
`diags/` or `chats/` in this session, say so; the opinion can still be
written but must not be labelled blind, and the chat file says why.

## 1. Build the blind pack

```
python3 harness/scripts/msdh.py blind-pack
```

This writes `scratch/blind_<date>.md`: profile, medications, specialists,
the full lab table, every lab provenance file, every visit and other file
with their *Harness notes* removed, and the symptom log and journal. It
contains everything humans and the patient have contributed and nothing a
model has concluded.

`scratch/` is not part of the record and is never committed.

## 2. Read it blind

Read the pack in full and nothing else from the record. Do not open
`SUMMARY.md`, `diags/`, `chats/`, or the *Harness notes* sections of the
originals. Do not look at `git log`; commit subjects name hypotheses.

## 3. Assess

Write your assessment to `scratch/opinion_<date>.md` first, so that it
exists before you see anyone else's view. Cover:

- **Problem list** as you see it, most consequential first.
- **Hypotheses**: each with the evidence for and against from the pack,
  your confidence in words, and what would settle it. Cross-field
  connections are the point; look for them deliberately.
- **Concerns about current management**: anything in the medication list
  or the specialists' plans that does not fit the data.
- **Gaps**: tests or history you would want and do not have.
- **Anything urgent**, which you also tell the patient now.

Ask the patient questions only if a fact in the pack is unclear. Do not
take a history; this is a chart review.

## 4. Unblind and compare

Now read `SUMMARY.md` and every `diags/` file. Then, for each of your
hypotheses:

- If a `diags/` file covers it, append an assessment there beginning with
  `Blind assessment.` and stating your view and confidence. If you agree,
  say what evidence you weighted; if you disagree, say exactly where the
  reasoning diverges.
- If none covers it, open a new `diags/` file with `status: hypothesis` and
  your assessment, also beginning with `Blind assessment.`

For each existing open hypothesis you did **not** arrive at: append an
assessment saying so, and whether, now that you see it, you find it
convincing. Silence is not a verdict.

If `git log` or the existing assessments show that your own model already
assessed this record, say so in each assessment: it is a re-assessment,
not an independent one.

## 5. Write the chat record

`chats/YYYY-MM-DD_second_opinion_<model-slug>.md`, `visit_kind:
second_opinion`. *Discussed* holds the blind assessment in full (copy it
from the scratch file). *Findings* holds the comparison: agreements,
disagreements, hypotheses new to the record, hypotheses you missed. *For
the doctors* lists what the disagreement, if any, means for the patient's
next appointments.

## 6. Tell the patient

Where the opinions agree, where they differ, and what you recommend doing
about the difference. Disagreement between models is information, not a
problem to be smoothed over.

## 7. Commit and tag

Follow `harness/procedures/commit.md` with `--procedure second-opinion`,
subject `blind assessment by <model>`, covering the `diags/` and `chats/`
files. Then `harness/procedures/summary-refresh.md`. Then tag:

```
python3 harness/scripts/msdh.py tag second-opinion-<date>-<model-slug> -m "blind assessment by <model>"
```

Delete nothing from `scratch/`; it is ignored by git and the patient may
want to read it.
