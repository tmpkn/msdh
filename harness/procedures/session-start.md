# Procedure: session-start

Runs at the beginning of every session, before anything else. It establishes
who you are, verifies the record is sane, and loads the patient into your
working context. Nothing is written to the record by this procedure.

## 1. Read the principles

Read `harness/PRINCIPLES.md` in full. It is short.

## 2. Establish your identity

Models are unreliable about their own identity, so the patient confirms it.

1. Form your best guess of your exact model ID and your runtime with version,
   using whatever your runtime exposes (system context, environment, your own
   knowledge). Model IDs look like `claude-fable-5-1`, `gpt-5.2`,
   `qwen-3.8-flash-next`. Runtimes look like `claude-code 2.1.0`,
   `codex 0.9.1`, `pi 1.4`.
2. Ask the patient, in one line, offering your guess as the default:
   *"Before we start: I believe I am running as `claude-fable-5-1` on
   `claude-code 2.1.0`. Correct?"*
3. Wait for the answer. If they correct you, use their values exactly.
4. Record it:

   ```
   python3 harness/scripts/msdh.py session --model <model> --runtime "<runtime>"
   ```

This identity is stamped on every file and commit for the rest of the
session. If the patient later says a different model is now running, that is
a new session: start this procedure again.

## 3. Check the record state

```
python3 harness/scripts/msdh.py status
```

Read every line of the output.

- **Not onboarded** (profile missing): skip to step 6 and offer onboarding.
  Do not perform any other procedure on an un-onboarded record.
- **Dirty tree**: stop. Do not build on top of it and do not clean it up on
  your own. Show the patient the list of changed files and `git diff --stat`.
  Explain that a previous session left uncommitted changes. The patient
  decides, and only the patient:
  - *finish and commit them*: inspect the diff, make sure you understand it,
    validate, then use `harness/procedures/commit.md` with
    `--procedure correction`;
  - *discard them*: run `git checkout -- <paths>` and `git clean -fd <paths>`
    only for the paths the patient names.
  Until the tree is clean, do not start any other procedure.
- **Stale session** is handled by step 2 already.

## 4. Validate

```
python3 harness/scripts/msdh.py validate
```

Errors mean a previous session wrote something the schemas reject. Report
them to the patient. A record with validation errors cannot be committed to,
so fixing them (with the patient's agreement, committed as a `correction`) is
the first order of business. Warnings are reported once and otherwise ignored.

## 5. Verify the remote is private

```
python3 harness/scripts/msdh.py check-remote
```

- `OK`: fine, say nothing.
- `FAIL`: tell the patient plainly that the origin is public and that you
  will not push. Everything else can proceed; the record stays local.
- `cannot verify`: ask the patient once, *"Is `<url>` a private repository?"*
  Remember the answer for the session. If they say no or are unsure, do not
  push.
- `WARNING: upstream is pushable`: run the command the warning gives,
  `git remote set-url --push upstream DISABLED`, and tell the patient you
  did. It changes no record content; it closes the one path by which a
  record could reach the public harness repository.

## 6. Load the patient

**If the patient has asked for a second opinion, stop here** and go to
`harness/procedures/second-opinion.md`. That procedure reads the record blind;
loading the summary and hypotheses now would defeat it.

Do not read the whole record. Read, in this order:

1. `SUMMARY.md` — the working memory. If it is missing on an onboarded
   record, note that summary-refresh is owed and do it before anything else
   in this session.
2. `profile/profile.md`, `profile/medications.csv`, `profile/specialists.csv`.
3. The frontmatter and `## Summary` section of every file in `diags/`, so you
   know the open hypotheses and their status.
4. `python3 harness/scripts/msdh.py symptoms` and
   `python3 harness/scripts/msdh.py labs list` for the shape of the data.
5. The most recent file in `chats/`, for continuity.

Read deeper, into individual visits, lab files and `data/labs_all.csv`, when
a question calls for it. `msdh.py labs trend <analyte>` is the fast path for
any "how has X been moving" question.

## 7. Greet

One short paragraph, no more:

- your confirmed identity;
- the state of the record: last commit date, anything pending from the
  summary's *Pending and recommended* section;
- if not onboarded: offer onboarding and nothing else;
- otherwise ask what the patient wants to do today.

Then route to the procedure in the `AGENTS.md` table.
