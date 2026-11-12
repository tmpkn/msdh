# Procedure: summary-refresh

Rewrites `SUMMARY.md`, the physician's working memory. Runs after every
commit that changes the record, as its own commit. Also runs on demand when
the patient asks, or at session start if the summary is missing or
predates the last record commit.

## 1. Check whether it is owed

```
git log -1 --format=%h
```

Compare with `record_commit` in the current `SUMMARY.md` frontmatter. If
they match, the summary is current; stop. If the file is missing or the
hashes differ, continue.

## 2. Read what feeds it

Read `harness/schemas/summary.md` for the exact sections. Then:

- `profile/profile.md` (identity, allergies, history),
  `profile/medications.csv` (rows with empty `end` are active),
  `profile/specialists.csv`.
- Every `diags/` file: frontmatter, `## Summary`, `## What would settle it`.
- `python3 harness/scripts/msdh.py symptoms` for the latest status of every
  symptom; the journal entries from the last few months for colour.
- `python3 harness/scripts/msdh.py labs list`, then
  `msdh.py labs trend <analyte>` for anything flagged in the most recent
  panels and anything on the current watch list.
- The last several files by date across `data/visits/`, `data/other/`,
  `chats/` for *Recent changes* and *Pending and recommended*.
- The previous `SUMMARY.md`, to carry forward items that are still true and
  to notice what has changed. Make a list of its *Pending and recommended*
  and *Watch list* items before you write; each one either reappears or is
  dropped for a reason you can name.

## 3. Write

Rewrite the file from scratch following the schema. Frontmatter:
`type: summary`, `date` = today, `created` = today, your identity,
`source: none`, `record_commit` = the hash from step 1.

Rules that matter here:

- Every statement traces to a record file. Link `diags/` files from the
  problem list and open hypotheses.
- Order problems by consequence, not by date.
- *Pending and recommended* names who acts: *"Patient: ask Dr Smith for a
  repeat ferritin"*, *"Dr Jones: thyroid ultrasound referral outstanding
  since 2026-09"*.
- *Watch list* is for drift that is not yet a problem. Give the span and the
  direction: *"ferritin falling, 88 to 31 over 2024-03 to 2026-11"*.
- A pending or watch-list item leaves the summary only when the record
  shows it done, superseded or no longer true, and the drop is named under
  *Recent changes* ("closed: urgent-care summary obtained, see ..."). The
  summary is the only place a patient sees what they still owe their
  doctors; an item forgotten here is forgotten everywhere.
- Keep it near one page. Prune *Recent changes* beyond ten entries. Length
  is a ceiling, not a target: do not pad a short summary and do not cut
  items to hit a line count. Tighten the wording instead.
- Nothing urgent lives only here. If writing the summary makes you notice
  something urgent, tell the patient now.

## 4. Commit

Follow `harness/procedures/commit.md`:

```
python3 harness/scripts/msdh.py commit --procedure summary-refresh -m "refresh after <what changed>" SUMMARY.md
```

The patient need not approve a summary refresh line by line; say in one
line that you are refreshing the summary and what changed in it.
