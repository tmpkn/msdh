# Procedure: onboarding

Creates a patient record from nothing. Runs once. Precondition: session-start
completed and `profile/profile.md` does not exist. If it exists, refuse and
point the patient to a visit instead, where profile facts can be updated.

Output: the profile, the care team, the medication list, any existing
diagnoses, current symptoms, an onboarding chat record, and the first
clinical summary. Two commits: the record, then the summary.

## 1. Set expectations

Two or three sentences. You are going to ask about them in a few rounds; it
takes a while; they can say "skip" to anything and add it later; nothing
leaves this directory except to their own private repository.

## 2. Intake, in rounds

Ask conversationally, one round at a time, and wait for each answer. Do not
dump the whole questionnaire. Adapt the order if the patient leads
elsewhere, but cover everything below before writing. Write "Unknown" or
"None reported" for what they skip.

**Round 1, who they are.** Name (as they want to be addressed), date of
birth, sex at birth and gender if different, height, current weight, blood
type if known.

**Round 2, what brought them here.** In their own words: what is going on,
what they are worried about, what the specialists have said and not said,
what they want from this. Listen. This becomes *Patient's own account* and
usually seeds the symptom log and the first hypotheses.

**Round 3, existing diagnoses and history.** Conditions diagnosed, by whom,
when, current status. Surgeries and procedures. Hospitalisations.

**Round 4, medications and supplements.** Everything they take, dose,
frequency, since when, who prescribed it, why. Include over-the-counter and
supplements. Ask specifically about anything stopped in the last year and
why.

**Round 5, allergies and intolerances.** Drugs, foods, environmental.
Reaction and how it was established.

**Round 6, family history.** Parents, siblings, grandparents, children:
significant conditions, age at onset, cause and age of death where relevant.

**Round 7, lifestyle.** Smoking, alcohol, other substances, exercise, diet,
sleep, occupation and exposures. Reproductive history where applicable.

**Round 8, the care team.** Every clinician they see: name, specialty,
institution, roughly since when, last visit.

**Round 9, current symptoms.** Everything bothering them now, each with
severity 0 to 10, how long, whether it is getting better or worse, what makes
it better or worse. Use `python3 harness/scripts/msdh.py symptoms` conventions
for naming: short, lowercase, reusable.

**Round 10, documents.** Do they have lab reports, letters, scans to bring
in? List what they mention under *Open questions* in the chat record.
Ingest is a separate procedure: finish onboarding first (steps 3 to 6),
then take the documents one by one through `ingest.md`. If the patient
wants to start committing before round 10, or to bring documents in before
answering it, close onboarding after round 9 and note the gap; round 10
then happens naturally as the documents arrive.

## 3. Write the record

Read the schemas before writing: `harness/schemas/profile.md`,
`symptoms.md`, `diag.md`, `chat.md`. Today's date is `created`; the
harness version is in `harness/VERSION`; your identity is what session-start
confirmed.

1. `profile/profile.md` — all sections, `type: profile`, `date` = today,
   `author_kind: patient`, `author: patient`, `source: none`.
2. `profile/medications.csv` — one row per medication, header row even if
   empty. `source` = `patient` for everything reported verbally.
3. `profile/specialists.csv` — one row per clinician, header row even if
   empty.
4. `symptoms/log.csv` — header row, then one row per current symptom with
   `status: new` and `source` = the chat file path from step 6.
5. `symptoms/YYYY-MM-DD_onboarding.md` — only if there are symptoms. The
   patient's narrative, then `## Logged`.
6. `chats/YYYY-MM-DD_onboarding.md` — `visit_kind: onboarding`. *Record
   changes* lists every file from this list. *For the doctors* and *Open
   questions* hold anything you noticed that deserves a question, and the
   documents they mentioned.
7. `diags/YYYY-MM-DD_<slug>.md` — one per existing diagnosis the patient
   reports. Status `confirmed` only if a named clinician made the diagnosis;
   that assessment is voiced as `human`, author `Dr Name (role)`, source the
   chat file, and its text says *"As reported by the patient during
   onboarding; no document on file."* Status `under_investigation` for
   things a clinician is currently working up. Add your own `model`
   assessment to each only if you have something to say beyond restating
   the patient; otherwise do not.
8. Hypotheses of your own from what you heard: open a `diags/` file with
   `status: hypothesis` for each, but only for cross-field observations
   worth a doctor's attention. Onboarding is not the place for speculative
   lists. Zero is a fine number.

Do not write `SUMMARY.md` yet.

## 4. Commit the record

Follow `harness/procedures/commit.md` with `--procedure onboarding` and the
subject `initial record for <first name>`. Present the file list to the
patient before committing; this is the first time they see what the record
looks like.

## 5. First summary

Follow `harness/procedures/summary-refresh.md`. It produces the second
commit.

## 6. Close

Tell the patient, briefly: the record exists, what is in it, how to bring
documents in (ingest), and that everything is committed with your model
identity in the log. If the remote is private, push per the commit
procedure. Suggest the next step is bringing in the most recent lab panel
and the most recent specialist letter.
