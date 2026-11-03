# Procedure: visit

A consultation. The patient wants to talk about how they are doing, work
through a problem, or review where things stand. This is the equivalent of
a doctor's appointment and it ends with a note in `chats/` plus whatever
the conversation changed in the record. Precondition: session-start
completed, record onboarded.

If the patient asked a quick question and it grows into this, say so in one
line ("this is becoming a proper consultation, I'll record it as one") and
continue here.

## 1. Prepare

Session-start loaded the summary. For a visit, also read in full:

- the most recent two files in `chats/`;
- every `diags/` file with status `hypothesis` or `under_investigation`;
- `symptoms/log.csv` rows from the last ninety days and the latest journal
  entry;
- any file the patient's opening words point to.

## 2. Open

Ask how they have been since the last consultation, naming the date and
one or two things that were open then. Then let them talk. Do not start
with a checklist.

## 3. Take the history

Work like a good generalist:

- Open questions first, then targeted ones. For each symptom: onset,
  course, character, severity 0 to 10, timing, triggers, relievers,
  associated features. Use existing symptom names from
  `python3 harness/scripts/msdh.py symptoms`; add new ones only for new
  things.
- Ask about medication changes and adherence, new doctors seen, tests done
  but not yet brought in, and anything they have been told since last time.
- When something is relevant to an open hypothesis, say so and ask the
  question that would move it.
- When the conversation touches a value in the record, look it up. Run
  `msdh.py labs trend <analyte>` rather than quoting from memory.

## 4. Reason across fields

Before concluding, do this deliberately, not as an afterthought:

- Walk every open hypothesis. Does anything from today bear on it, for or
  against? Say so to the patient.
- Ask what each specialist is not seeing. Which findings from one field
  would change another field's interpretation? Which symptom has been
  attributed to one condition by default, without that being tested?
- Separate what you observed from what you infer, and give your confidence
  in words: *likely*, *possible*, *worth excluding*.
- Anything urgent is said first and plainly, with the advice to seek care
  now. Do not soften it and do not bury it in the note.

Your output is hypotheses, questions for named doctors, and tests worth
requesting, with the reason for each. Not diagnoses.

## 5. Close the conversation

Summarise back to the patient in a few sentences: what you heard, what you
think, what you suggest they do next and with whom. Ask if you missed
anything. Then say you will write it up.

## 6. Write the record

Read the schemas before writing. Everything below carries your session
identity and today's date as `created`.

1. `symptoms/log.csv`: one row per symptom discussed, with today's date,
   current status, and `source` = the chat file path from item 5. A symptom
   not discussed is not re-logged.
2. `symptoms/YYYY-MM-DD_<slug>.md`: a journal entry in the patient's words,
   with `## Logged` listing the rows added. Skip only if no symptoms were
   discussed.
3. `profile/medications.csv` for any change, `profile/profile.md` for any
   changed fact, with a changelog line. `profile/specialists.csv` for any
   new clinician.
4. `diags/`: append a `model` assessment to every open hypothesis you
   reasoned about, even if the conclusion is "unchanged". Open a new file
   for each new hypothesis worth a doctor's time. Change status to
   `under_investigation` when the patient reports a clinician is now
   working on it; never to `confirmed`.
5. `chats/YYYY-MM-DD_<slug>.md`, `visit_kind: consultation` (or `review`
   when the visit was a periodic look at the whole record rather than a
   problem). *Record changes* lists every file above. *For the doctors* is
   concrete: which clinician, what to ask, what to request, why.

## 7. Commit

Follow `harness/procedures/commit.md` with `--procedure visit` and a
subject that names the topic: `consultation on fatigue and palpitations`.
Then `harness/procedures/summary-refresh.md`.
