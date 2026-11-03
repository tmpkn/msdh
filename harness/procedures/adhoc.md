# Procedure: adhoc

A quick question, answered by the physician who knows this patient. No
questionnaire, no write-up of the conversation. Precondition: session-start
completed, record onboarded.

## 1. Answer the question

Answer from the context session-start loaded, and read deeper when the
question calls for it: the relevant `diags/` file, the trend of an analyte
(`msdh.py labs trend`), the last visit with the relevant specialist.

The answer must be the answer of someone who has read this patient's
record, not a general one. Tie it to their facts: their medications, their
values and how they have moved, their open hypotheses, what their
specialists have said. If the record does not support an answer, say that,
and say what would.

Keep it short. Urgent things first, in plain words, with the advice to seek
care now if that is what the situation calls for.

## 2. Record the facts the question revealed

Conversations are not logged; facts are. Before you finish, ask yourself
whether the patient told you anything that belongs in the record:

- **A new or changed symptom.** Write a short journal entry
  `symptoms/YYYY-MM-DD_<slug>.md` in the patient's words with a `## Logged`
  section, and add the row(s) to `symptoms/log.csv` with `source` = the
  journal entry path.
- **A medication change.** A row in `profile/medications.csv`, `source` =
  `patient`; `end` date on the old row if it was replaced.
- **A changed profile fact** (weight, new allergy, new diagnosis from a
  doctor). Edit `profile/profile.md` in place and add a changelog line. A
  doctor's new diagnosis also gets a `diags/` entry with a `human`
  assessment, source `profile/profile.md`, marked as patient-reported with
  no document on file.
- **A visit happened or a result arrived.** Do not reconstruct it here.
  Tell the patient to bring the document and ingest it, or to tell you
  about the visit properly so it can be recorded as one. Note it in the
  summary's pending section at the next refresh.

If nothing new was said, write nothing.

## 3. Commit, if anything was written

Follow `harness/procedures/commit.md` with `--procedure adhoc` and a
subject naming the fact: `noted new headache, severity 4`, `noted
levothyroxine increased to 100 mcg by Dr Lee`. A one-line "I've noted that
in your record" is enough of a review for a single fact. Then
`harness/procedures/summary-refresh.md` if the fact belongs in the summary,
which a medication change or new symptom always does.

## 4. Know when to promote

If the patient keeps going, if several facts come out, or if answering
properly needs real reasoning across the record, this has become a visit.
Say so in one line and switch to `harness/procedures/visit.md`.
